"""
Name: Ingest Document Use Case

Responsibilities:
  - Orchestrate document ingestion: validate → chunk → embed → persist
  - Enforce workspace write access
  - Split text into semantic chunks using TextChunkerService
  - Generate embeddings for each chunk in batch
  - Persist document + chunks atomically via repository
  - Return document_id and chunks_created count

Collaborators:
  - domain/repositories.DocumentRepository: atomic persistence
  - domain.repositories.WorkspaceRepository
  - domain.workspace_policy
  - domain/services.EmbeddingService: batch embedding
  - domain/services.TextChunkerService: text splitting

Constraints:
  - Text must be non-empty (empty chunks saved with count=0)
  - Title required, source/metadata optional
  - Transaction must be atomic (all or nothing)
  - Must NOT call external APIs if chunking returns empty

Notes:
  - Chunking defaults: 900 chars, 120 overlap
  - Embedding batch size limited by Google API quotas
  - Output includes UUID for subsequent retrieval/search
"""

from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Dict, Any, List, Optional

from ....domain.entities import Document, Chunk
from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.services import EmbeddingService, TextChunkerService
from ....domain.tags import normalize_tags
from ....domain.access import normalize_allowed_roles
from ....domain.workspace_policy import WorkspaceActor
from ....crosscutting.metrics import record_prompt_injection_detected
from ...prompt_injection_detector import detect
from ..documents.document_results import DocumentError, DocumentErrorCode, IngestDocumentResult
from ..workspace.workspace_access import resolve_workspace_for_write


@dataclass
class IngestDocumentInput:
    workspace_id: UUID
    actor: WorkspaceActor | None
    title: str
    text: str
    source: Optional[str] = None
    metadata: Dict[str, Any] | None = None


class IngestDocumentUseCase:
    """
    R: Use case for document ingestion.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        embedding_service: EmbeddingService,
        chunker: TextChunkerService,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.embedding_service = embedding_service
        self.chunker = chunker

    def execute(self, input_data: IngestDocumentInput) -> IngestDocumentResult:
        if not input_data.workspace_id:
            return IngestDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.VALIDATION_ERROR,
                    message="workspace_id is required",
                    resource="Workspace",
                )
            )
        _, error = resolve_workspace_for_write(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self.workspace_repository,
        )
        if error:
            return IngestDocumentResult(error=error)

        doc_id = uuid4()
        metadata = dict(input_data.metadata or {})
        tags = normalize_tags(metadata)
        allowed_roles = normalize_allowed_roles(metadata)

        document = Document(
            id=doc_id,
            workspace_id=input_data.workspace_id,
            title=input_data.title,
            source=input_data.source,
            metadata=metadata,
            tags=tags,
            allowed_roles=allowed_roles,
        )

        chunks = self.chunker.chunk(input_data.text)
        if not chunks:
            # R: No chunks - save document only (atomic with empty chunks list)
            self.repository.save_document_with_chunks(document, [])
            return IngestDocumentResult(
                document_id=doc_id,
                chunks_created=0,
            )

        embeddings = self.embedding_service.embed_batch(chunks)

        detected_flags: set[str] = set()
        detected_patterns: set[str] = set()
        max_risk_score = 0.0

        chunk_entities: List[Chunk] = []
        for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
            detection = detect(content)
            chunk_metadata = {}
            if detection.patterns:
                chunk_metadata = {
                    "security_flags": detection.flags,
                    "risk_score": detection.risk_score,
                    "detected_patterns": detection.patterns,
                }
                for pattern in detection.patterns:
                    record_prompt_injection_detected(pattern)
                detected_flags.update(detection.flags)
                detected_patterns.update(detection.patterns)
                max_risk_score = max(max_risk_score, detection.risk_score)

            chunk_entities.append(
                Chunk(
                    content=content,
                    embedding=embedding,
                    document_id=doc_id,
                    chunk_index=index,
                    metadata=chunk_metadata,
                )
            )

        if detected_patterns:
            metadata["rag_security"] = {
                "security_flags": sorted(detected_flags),
                "risk_score": round(max_risk_score, 4),
                "detected_patterns": sorted(detected_patterns),
            }

        # R: Atomic save - document and chunks in single transaction
        self.repository.save_document_with_chunks(document, chunk_entities)

        return IngestDocumentResult(
            document_id=doc_id,
            chunks_created=len(chunk_entities),
        )
