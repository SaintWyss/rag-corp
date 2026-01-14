"""
Name: Ingest Document Use Case

Responsibilities:
  - Orchestrate document ingestion: validate → chunk → embed → persist
  - Split text into semantic chunks using TextChunkerService
  - Generate embeddings for each chunk in batch
  - Persist document + chunks atomically via repository
  - Return document_id and chunks_created count

Collaborators:
  - domain/repositories.DocumentRepository: atomic persistence
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

from ...domain.entities import Document, Chunk
from ...domain.repositories import DocumentRepository
from ...domain.services import EmbeddingService, TextChunkerService
from ...domain.tags import normalize_tags


@dataclass
class IngestDocumentInput:
    title: str
    text: str
    source: Optional[str] = None
    metadata: Dict[str, Any] | None = None


@dataclass
class IngestDocumentOutput:
    document_id: UUID
    chunks_created: int


class IngestDocumentUseCase:
    """
    R: Use case for document ingestion.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
        chunker: TextChunkerService,
    ):
        self.repository = repository
        self.embedding_service = embedding_service
        self.chunker = chunker

    def execute(self, input_data: IngestDocumentInput) -> IngestDocumentOutput:
        doc_id = uuid4()
        metadata = input_data.metadata or {}
        tags = normalize_tags(metadata)

        document = Document(
            id=doc_id,
            title=input_data.title,
            source=input_data.source,
            metadata=metadata,
            tags=tags,
        )

        chunks = self.chunker.chunk(input_data.text)
        if not chunks:
            # R: No chunks - save document only (atomic with empty chunks list)
            self.repository.save_document_with_chunks(document, [])
            return IngestDocumentOutput(
                document_id=doc_id,
                chunks_created=0,
            )

        embeddings = self.embedding_service.embed_batch(chunks)

        chunk_entities: List[Chunk] = [
            Chunk(
                content=content,
                embedding=embedding,
                document_id=doc_id,
                chunk_index=index,
            )
            for index, (content, embedding) in enumerate(zip(chunks, embeddings))
        ]

        # R: Atomic save - document and chunks in single transaction
        self.repository.save_document_with_chunks(document, chunk_entities)

        return IngestDocumentOutput(
            document_id=doc_id,
            chunks_created=len(chunk_entities),
        )
