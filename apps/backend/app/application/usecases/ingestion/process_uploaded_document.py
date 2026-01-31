"""
===============================================================================
USE CASE: Process Uploaded Document (Async Pipeline)
===============================================================================

Name:
    Process Uploaded Document Use Case

Business Goal:
    Procesar asíncronamente un documento previamente subido (upload), ejecutando:
      - descarga del archivo desde storage
      - extracción de texto
      - chunking semántico
      - embeddings batch
      - persistencia de chunks (reemplazando los anteriores)
      - transición de estados del documento:
          PENDING/FAILED/None -> PROCESSING -> READY | FAILED

Why (Context / Intención):
    - Upload y procesamiento son pasos separados (pipeline asíncrono).
    - Se necesita robustez ante reintentos y ejecución concurrente:
        * idempotencia (si ya READY, no reprocesar)
        * lock lógico (transición atómica a PROCESSING)
    - Se debe persistir error_message truncado para evitar logs/payloads enormes.
    - El pipeline añade metadata de seguridad por chunk y registra métricas
      cuando se detectan patrones de prompt injection.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ProcessUploadedDocumentUseCase

Responsibilities:
    - Validar input mínimo (workspace_id, document_id).
    - Recuperar documento y manejar casos faltantes (MISSING).
    - Aplicar idempotencia por status (READY/PROCESSING).
    - Obtener lock lógico con transition_document_status(... -> PROCESSING).
    - Validar configuración de storage y metadata del documento (storage_key/mime).
    - Descargar archivo y extraer texto.
    - Chunking y reemplazo de chunks anteriores.
    - Generar embeddings batch (solo si hay chunks).
    - Aplicar detección de prompt injection por chunk:
        * agregar metadata al chunk
        * registrar métricas por patrón detectado
    - Persistir chunks y transicionar estado a READY.
    - Capturar errores, truncarlos y transicionar a FAILED.

Collaborators:
    - DocumentRepository:
        get_document(document_id, workspace_id)
        transition_document_status(... from_statuses, to_status, error_message)
        delete_chunks_for_document(document_id, workspace_id)
        save_chunks(document_id, chunk_entities, workspace_id)
    - FileStoragePort:
        download_file(storage_key) -> bytes
    - DocumentTextExtractor:
        extract_text(mime_type, content_bytes) -> str
    - TextChunkerService:
        chunk(text) -> list[str]
    - EmbeddingService:
        embed_batch(chunks) -> list[list[float]]
    - prompt_injection_detector.detect:
        detect(text) -> detection(flags, risk_score, patterns)
    - record_prompt_injection_detected(pattern):
        métrica por patrón

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - ProcessUploadedDocumentInput:
        document_id: UUID
        workspace_id: UUID

Outputs:
    - ProcessUploadedDocumentOutput:
        status: str
        chunks_created: int

Status semantics:
    - "MISSING": no se encontró el documento
    - "READY": ya procesado / o procesado exitosamente en esta ejecución
    - "PROCESSING": ya estaba en proceso (otro worker)
    - "FAILED": falló el pipeline
    - "UNKNOWN": estado inesperado cuando no se pudo transicionar a PROCESSING
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from ....crosscutting.metrics import record_prompt_injection_detected
from ....domain.entities import Chunk
from ....domain.repositories import DocumentRepository
from ....domain.services import (
    DocumentTextExtractor,
    EmbeddingService,
    FileStoragePort,
    TextChunkerService,
)
from ...prompt_injection_detector import detect

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constantes: evitan magic numbers/strings dispersos.
# -----------------------------------------------------------------------------
MAX_ERROR_MESSAGE_LEN: Final[int] = 500

STATUS_PENDING: Final[str] = "PENDING"
STATUS_PROCESSING: Final[str] = "PROCESSING"
STATUS_READY: Final[str] = "READY"
STATUS_FAILED: Final[str] = "FAILED"

STATUS_MISSING: Final[str] = "MISSING"
STATUS_UNKNOWN: Final[str] = "UNKNOWN"


@dataclass(frozen=True)
class ProcessUploadedDocumentInput:
    """
    DTO de entrada para procesamiento asíncrono.

    Notas:
      - workspace_id se usa para scoping del documento (seguridad/consistencia).
    """

    document_id: UUID
    workspace_id: UUID


@dataclass(frozen=True)
class ProcessUploadedDocumentOutput:
    """
    DTO de salida del worker.

    Campos:
      - status: estado final observado o resultante
      - chunks_created: cantidad de chunks persistidos en esta ejecución
    """

    status: str
    chunks_created: int


def _truncate_error(message: str, max_len: int = MAX_ERROR_MESSAGE_LEN) -> str:
    """
    Trunca el mensaje de error para evitar guardar strings enormes.

    Motivo:
      - Los errores pueden incluir trazas o payloads largos.
      - Mantener una cota protege la DB y mejora observabilidad.
    """
    value = (message or "").strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


class ProcessUploadedDocumentUseCase:
    """
    Use Case (Application Service / Worker Command):
        Procesa el documento subido ejecutando el pipeline de extracción,
        chunking y embeddings, con transiciones de estado robustas.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        storage: FileStoragePort | None,
        extractor: DocumentTextExtractor,
        chunker: TextChunkerService,
        embedding_service: EmbeddingService,
    ) -> None:
        self._documents = repository
        self._storage = storage
        self._extractor = extractor
        self._chunker = chunker
        self._embeddings = embedding_service

    def execute(
        self, input_data: ProcessUploadedDocumentInput
    ) -> ProcessUploadedDocumentOutput:
        """
        Ejecuta el procesamiento del documento.

        Estrategia de concurrencia:
          - Se evita doble procesamiento usando una transición atómica a PROCESSING.
          - Si el documento ya está READY o PROCESSING, se devuelve ese status.

        Estrategia de fallos:
          - Ante excepción: se setea FAILED con error_message truncado.
        """

        # ---------------------------------------------------------------------
        # 1) Validación mínima.
        # ---------------------------------------------------------------------
        if not input_data.workspace_id:
            logger.error("Process document: workspace_id is required")
            return ProcessUploadedDocumentOutput(status=STATUS_FAILED, chunks_created=0)

        document_id = input_data.document_id

        # ---------------------------------------------------------------------
        # 2) Cargar documento (scoped por workspace).
        # ---------------------------------------------------------------------
        document = self._documents.get_document(
            document_id, workspace_id=input_data.workspace_id
        )
        if document is None:
            logger.warning(
                "Process document: not found", extra={"document_id": str(document_id)}
            )
            return ProcessUploadedDocumentOutput(
                status=STATUS_MISSING, chunks_created=0
            )

        workspace_id = document.workspace_id

        # ---------------------------------------------------------------------
        # 3) Idempotencia: si ya está listo o en progreso, no reprocesar.
        # ---------------------------------------------------------------------
        if document.status == STATUS_READY:
            return ProcessUploadedDocumentOutput(status=STATUS_READY, chunks_created=0)

        if document.status == STATUS_PROCESSING:
            return ProcessUploadedDocumentOutput(
                status=STATUS_PROCESSING, chunks_created=0
            )

        # ---------------------------------------------------------------------
        # 4) Lock lógico: transición a PROCESSING (atómica en repositorio).
        # ---------------------------------------------------------------------
        # from_statuses incluye None para documentos recién creados sin status.
        transitioned = self._documents.transition_document_status(
            document_id,
            workspace_id=workspace_id,
            from_statuses=[None, STATUS_PENDING, STATUS_FAILED],
            to_status=STATUS_PROCESSING,
            error_message=None,
        )

        if not transitioned:
            # Otro proceso pudo haber cambiado el status entre la lectura y este punto.
            # Devolvemos el status observado originalmente como mejor señal disponible.
            return ProcessUploadedDocumentOutput(
                status=document.status or STATUS_UNKNOWN, chunks_created=0
            )

        # A partir de acá, el documento está "reservado" para este worker.
        chunks_created = 0

        try:
            # -----------------------------------------------------------------
            # 5) Validar configuración de storage y metadata obligatoria.
            # -----------------------------------------------------------------
            if self._storage is None:
                raise RuntimeError("File storage not configured")

            if not document.storage_key or not document.mime_type:
                raise ValueError("Missing file metadata for processing")

            # -----------------------------------------------------------------
            # 6) Descargar archivo y extraer texto.
            # -----------------------------------------------------------------
            content_bytes = self._storage.download_file(document.storage_key)
            text = self._extractor.extract_text(document.mime_type, content_bytes)

            # -----------------------------------------------------------------
            # 7) Chunking.
            # -----------------------------------------------------------------
            # Si el extractor devuelve texto vacío, chunker debe devolver [].
            chunks_text = self._chunker.chunk(text or "")

            # -----------------------------------------------------------------
            # 8) Reemplazar chunks existentes (re-procesamiento seguro).
            # -----------------------------------------------------------------
            # Motivo: si el documento se reprocesa, no queremos chunks duplicados.
            self._documents.delete_chunks_for_document(
                document_id, workspace_id=workspace_id
            )

            # -----------------------------------------------------------------
            # 9) Embeddings + construcción de entidades Chunk (solo si hay chunks).
            # -----------------------------------------------------------------
            if chunks_text:
                embeddings = self._embeddings.embed_batch(chunks_text)

                # Defensa: contrato esperado es 1 embedding por chunk.
                if len(embeddings) != len(chunks_text):
                    raise RuntimeError("Embedding batch size mismatch")

                chunk_entities = self._build_chunk_entities(
                    document_id=document_id,
                    chunks_text=chunks_text,
                    embeddings=embeddings,
                )

                self._documents.save_chunks(
                    document_id, chunk_entities, workspace_id=workspace_id
                )
                chunks_created = len(chunk_entities)

            # -----------------------------------------------------------------
            # 10) Finalizar estado a READY.
            # -----------------------------------------------------------------
            self._documents.transition_document_status(
                document_id,
                workspace_id=workspace_id,
                from_statuses=[STATUS_PROCESSING],
                to_status=STATUS_READY,
                error_message=None,
            )

            return ProcessUploadedDocumentOutput(
                status=STATUS_READY, chunks_created=chunks_created
            )

        except Exception as exc:
            # -----------------------------------------------------------------
            # Manejo de errores: FAILED + error_message truncado.
            # -----------------------------------------------------------------
            error_message = _truncate_error(str(exc))
            self._documents.transition_document_status(
                document_id,
                workspace_id=workspace_id,
                from_statuses=[STATUS_PROCESSING],
                to_status=STATUS_FAILED,
                error_message=error_message,
            )

            logger.exception(
                "Process document failed", extra={"document_id": str(document_id)}
            )
            return ProcessUploadedDocumentOutput(status=STATUS_FAILED, chunks_created=0)

    # =========================================================================
    # Helpers privados: separan construcción de chunks y seguridad.
    # =========================================================================

    @staticmethod
    def _build_chunk_entities(
        *,
        document_id: UUID,
        chunks_text: list[str],
        embeddings: list[list[float]],
    ) -> list[Chunk]:
        """
        Construye entidades Chunk con metadata de seguridad si se detectan patrones.

        Por cada chunk:
          - detect(content_text)
          - si hay patterns:
              * adjuntar security_flags, risk_score, detected_patterns
              * registrar métrica por pattern

        Nota:
          - A diferencia del use case de ingest, aquí no agregamos un resumen
            agregado al documento; este worker se enfoca en chunks persistidos.
        """
        chunk_entities: list[Chunk] = []

        for index, (content_text, embedding) in enumerate(zip(chunks_text, embeddings)):
            detection = detect(content_text)

            chunk_metadata: dict = {}
            if detection.patterns:
                chunk_metadata = {
                    "security_flags": detection.flags,
                    "risk_score": detection.risk_score,
                    "detected_patterns": detection.patterns,
                }
                for pattern in detection.patterns:
                    record_prompt_injection_detected(pattern)

            chunk_entities.append(
                Chunk(
                    content=content_text,
                    embedding=embedding,
                    document_id=document_id,
                    chunk_index=index,
                    metadata=chunk_metadata,
                )
            )

        return chunk_entities
