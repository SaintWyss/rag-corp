"""
===============================================================================
USE CASE: Ingest Document (Validate → Chunk → Embed → Persist)
===============================================================================

Name:
    Ingest Document Use Case

Business Goal:
    Ingerir un documento dentro de un workspace (con acceso de escritura),
    transformando un texto en chunks semánticos, generando embeddings y
    persistiendo el documento + chunks de forma atómica.

What this use case guarantees (invariantes):
  1) Workspace write access is enforced (central policy).
  2) Title is required (document identity/meaning).
  3) External services (Embedding API) are NOT called if there are no chunks.
     - This includes empty/blank input text.
  4) Persistence is atomic via repository contract:
     - The repository must save Document + Chunks in one transaction (all-or-nothing).
  5) Output always returns:
     - document_id (UUID)
     - chunks_created (int)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    IngestDocumentUseCase

Responsibilities:
    - Validate input (workspace_id, title, minimal text handling).
    - Enforce workspace write access through shared access helper.
    - Normalize metadata → tags + allowed_roles.
    - Build Document entity.
    - Chunk text via TextChunkerService.
    - If no chunks: persist Document with empty chunks atomically.
    - If chunks: generate embeddings in batch via EmbeddingService.
    - Perform prompt-injection detection per chunk and:
        * attach security metadata to the chunk when patterns are detected
        * aggregate a workspace-level rag_security summary into document metadata
        * record metrics per detected pattern
    - Persist Document + Chunks atomically.
    - Return IngestDocumentResult with document_id and chunks_created.

Collaborators:
    - WorkspaceRepository (via resolve_workspace_for_write)
    - DocumentRepository:
        save_document_with_chunks(document, chunks)  # atomic contract
    - TextChunkerService:
        chunk(text) -> list[str]
    - EmbeddingService:
        embed_batch(texts) -> list[list[float]]  # same length as inputs
    - prompt_injection_detector.detect:
        detect(content) -> detection(flags, risk_score, patterns)
    - record_prompt_injection_detected(pattern):
        metric counter for each detected pattern
    - normalize_tags(metadata):
        derive tags from metadata
    - normalize_allowed_roles(metadata):
        derive allowed_roles from metadata

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    IngestDocumentInput:
      - workspace_id: UUID
      - actor: WorkspaceActor | None
      - title: str
      - text: str
      - source: Optional[str]
      - metadata: Optional[dict[str, Any]]

Outputs:
    IngestDocumentResult:
      - document_id: UUID | None
      - chunks_created: int
      - error: DocumentError | None

Error Mapping:
    - VALIDATION_ERROR:
        * workspace_id missing/invalid
        * title missing/blank
      (text blank is allowed: produces 0 chunks and no external calls)
    - FORBIDDEN / NOT_FOUND:
        * returned by workspace access helper (consistent enforcement)
    - SERVICE_UNAVAILABLE:
        * embedding service failure (external dependency)
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Final, Optional
from uuid import UUID, uuid4

from ....crosscutting.metrics import record_prompt_injection_detected
from ....domain.access import normalize_allowed_roles
from ....domain.entities import Chunk, Document
from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.services import EmbeddingService, TextChunkerService
from ....domain.tags import normalize_tags
from ....domain.workspace_policy import WorkspaceActor
from ...prompt_injection_detector import detect
from ..documents.document_results import (
    DocumentError,
    DocumentErrorCode,
    IngestDocumentResult,
)
from ..workspace.workspace_access import resolve_workspace_for_write

_RESOURCE_WORKSPACE: Final[str] = "Workspace"
_MSG_WORKSPACE_ID_REQUIRED: Final[str] = "workspace_id is required"
_MSG_TITLE_REQUIRED: Final[str] = "title is required"
_SECURITY_DOC_KEY: Final[str] = "rag_security"


@dataclass(frozen=True)
class IngestDocumentInput:
    """
    DTO de entrada para ingesta.

    Notas:
      - metadata es copiada a un dict propio para evitar efectos colaterales.
      - title es obligatorio.
      - text puede ser vacío/blanco: se persiste el documento con 0 chunks y
        NO se invoca embedding (cumple restricción de no llamar APIs externas).
    """

    workspace_id: UUID
    actor: WorkspaceActor | None
    title: str
    text: str
    source: Optional[str] = None
    metadata: Dict[str, Any] | None = None


class IngestDocumentUseCase:
    """
    Use Case (Application Service / Command):
        Orquesta la ingesta de un documento (pipeline controlado).
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        embedding_service: EmbeddingService,
        chunker: TextChunkerService,
    ) -> None:
        self._documents = repository
        self._workspaces = workspace_repository
        self._embeddings = embedding_service
        self._chunker = chunker

    def execute(self, input_data: IngestDocumentInput) -> IngestDocumentResult:
        """
        Ejecuta la ingesta y devuelve el resultado tipado.

        Orden de operaciones (minimiza costo y reduce fallos):
          1) Validar input mínimo.
          2) Resolver acceso de escritura al workspace.
          3) Construir Document (id, metadata normalizada, tags, allowed_roles).
          4) Chunking.
          5) Si no hay chunks: persistir documento (sin servicios externos).
          6) Si hay chunks: embeddings batch + seguridad por chunk.
          7) Persistir documento+chunks de forma atómica.
        """

        # ---------------------------------------------------------------------
        # 1) Validaciones mínimas (baratas) antes de tocar repos o servicios.
        # ---------------------------------------------------------------------
        validation_error = self._validate_input(input_data)
        if validation_error is not None:
            return IngestDocumentResult(error=validation_error)

        # ---------------------------------------------------------------------
        # 2) Enforce acceso de escritura al workspace (seguridad centralizada).
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_write(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self._workspaces,
        )
        if workspace_error is not None:
            return IngestDocumentResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 3) Construcción de entidades de dominio (Document + metadata normalizada).
        # ---------------------------------------------------------------------
        document_id = uuid4()
        document, document_metadata = self._build_document(
            document_id=document_id,
            input_data=input_data,
        )

        # ---------------------------------------------------------------------
        # 4) Chunking (sin dependencias externas).
        # ---------------------------------------------------------------------
        chunks_text = self._chunk_text(input_data.text)

        # ---------------------------------------------------------------------
        # 5) Si no hay chunks, NO llamar servicios externos.
        # ---------------------------------------------------------------------
        if not chunks_text:
            # Persistencia atómica por contrato del repositorio.
            self._documents.save_document_with_chunks(document, [])
            return IngestDocumentResult(document_id=document_id, chunks_created=0)

        # ---------------------------------------------------------------------
        # 6) Embeddings batch + análisis de seguridad por chunk.
        # ---------------------------------------------------------------------
        # Restricción: batch size/quota debe manejarse dentro de EmbeddingService.
        embeddings = self._embed_chunks(chunks_text)
        if embeddings is None:
            return IngestDocumentResult(error=self._service_unavailable_error())

        chunk_entities, security_summary = self._build_chunk_entities_with_security(
            document_id=document_id,
            chunks_text=chunks_text,
            embeddings=embeddings,
        )

        # Adjuntamos resumen de seguridad al metadata del documento si hay hallazgos.
        if security_summary is not None:
            document_metadata[_SECURITY_DOC_KEY] = security_summary
            # Importante: document.metadata apunta a document_metadata (mutable),
            # así que ya quedó actualizado en la entidad `document`.

        # ---------------------------------------------------------------------
        # 7) Persistencia atómica (Documento + Chunks).
        # ---------------------------------------------------------------------
        self._documents.save_document_with_chunks(document, chunk_entities)

        return IngestDocumentResult(
            document_id=document_id,
            chunks_created=len(chunk_entities),
        )

    # =========================================================================
    # Helpers privados: mantienen execute() legible y encapsulan reglas.
    # =========================================================================

    @staticmethod
    def _validate_input(input_data: IngestDocumentInput) -> DocumentError | None:
        """
        Valida campos obligatorios para ejecutar el use case.

        Reglas:
          - workspace_id requerido
          - title requerido (no vacío luego de strip)
          - text puede ser vacío/blanco (se permite: 0 chunks y no embedding)
        """
        if not input_data.workspace_id:
            return DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=_MSG_WORKSPACE_ID_REQUIRED,
                resource=_RESOURCE_WORKSPACE,
            )

        if not (input_data.title or "").strip():
            return DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=_MSG_TITLE_REQUIRED,
                resource="Document",
            )

        return None

    def _build_document(
        self, *, document_id: UUID, input_data: IngestDocumentInput
    ) -> tuple[Document, Dict[str, Any]]:
        """
        Construye la entidad Document asegurando metadata normalizada.

        Nota:
          - Se copia metadata para evitar mutaciones a estructuras externas.
          - tags y allowed_roles se derivan de metadata (normalizadores de dominio).
        """
        metadata: Dict[str, Any] = dict(input_data.metadata or {})
        tags = normalize_tags(metadata)
        allowed_roles = normalize_allowed_roles(metadata)

        document = Document(
            id=document_id,
            workspace_id=input_data.workspace_id,
            title=input_data.title.strip(),
            source=input_data.source,
            metadata=metadata,
            tags=tags,
            allowed_roles=allowed_roles,
        )
        return document, metadata

    def _chunk_text(self, text: str) -> list[str]:
        """
        Ejecuta chunking semántico.

        Regla importante:
          - Si text es vacío/blanco → devuelve lista vacía (0 chunks).
            Esto evita invocar embeddings y cumple la restricción de no llamar
            APIs externas si no hay chunks.
        """
        normalized_text = (text or "").strip()
        if not normalized_text:
            return []
        return self._chunker.chunk(normalized_text)

    def _embed_chunks(self, chunks_text: list[str]) -> list[list[float]] | None:
        """
        Genera embeddings batch para los chunks.

        Manejo de fallas:
          - Si el embedding service falla (excepción), devolvemos None y el caller
            responde SERVICE_UNAVAILABLE.
        """
        try:
            embeddings = self._embeddings.embed_batch(chunks_text)
        except Exception:
            return None

        # Defensa: el contrato esperado es 1 embedding por chunk.
        if len(embeddings) != len(chunks_text):
            return None

        return embeddings

    def _build_chunk_entities_with_security(
        self,
        *,
        document_id: UUID,
        chunks_text: list[str],
        embeddings: list[list[float]],
    ) -> tuple[list[Chunk], dict[str, Any] | None]:
        """
        Construye entidades Chunk y aplica detección de prompt injection.

        Estrategia:
          - Por cada chunk:
              * correr detect(content)
              * si hay patterns: adjuntar metadata de seguridad al chunk
              * registrar métricas por pattern detectado
          - Se agrega un resumen agregado en el documento:
              rag_security = {security_flags, risk_score, detected_patterns}
            solo si se detectó algo.

        Devuelve:
          - chunk_entities: list[Chunk]
          - security_summary: dict | None
        """
        detected_flags: set[str] = set()
        detected_patterns: set[str] = set()
        max_risk_score: float = 0.0

        chunk_entities: list[Chunk] = []

        for index, (content, embedding) in enumerate(zip(chunks_text, embeddings)):
            detection = detect(content)

            chunk_metadata: dict[str, Any] = {}
            if detection.patterns:
                # Metadata por chunk para auditoría puntual.
                chunk_metadata = {
                    "security_flags": detection.flags,
                    "risk_score": detection.risk_score,
                    "detected_patterns": detection.patterns,
                }

                # Métricas por patrón detectado (observabilidad).
                for pattern in detection.patterns:
                    record_prompt_injection_detected(pattern)

                detected_flags.update(detection.flags)
                detected_patterns.update(detection.patterns)
                max_risk_score = max(max_risk_score, float(detection.risk_score))

            chunk_entities.append(
                Chunk(
                    content=content,
                    embedding=embedding,
                    document_id=document_id,
                    chunk_index=index,
                    metadata=chunk_metadata,
                )
            )

        # Resumen agregado (solo si hay hallazgos).
        if not detected_patterns:
            return chunk_entities, None

        security_summary: dict[str, Any] = {
            "security_flags": sorted(detected_flags),
            "risk_score": round(max_risk_score, 4),
            "detected_patterns": sorted(detected_patterns),
        }
        return chunk_entities, security_summary

    @staticmethod
    def _service_unavailable_error() -> DocumentError:
        """
        Error consistente cuando una dependencia externa (embeddings) falla.
        """
        return DocumentError(
            code=DocumentErrorCode.SERVICE_UNAVAILABLE,
            message="Embedding service is unavailable.",
            resource="EmbeddingService",
        )
