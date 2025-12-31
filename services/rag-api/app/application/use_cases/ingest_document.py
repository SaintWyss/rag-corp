"""
Name: Ingest Document Use Case

Responsibilities:
  - Orchestrate document ingestion (chunk → embed → store)
  - Coordinate repository, embedding service, and chunker
  - Return document id and chunk count
"""

from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Dict, Any, List, Optional

from ...domain.entities import Document, Chunk
from ...domain.repositories import DocumentRepository
from ...domain.services import EmbeddingService, TextChunkerService


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

        document = Document(
            id=doc_id,
            title=input_data.title,
            source=input_data.source,
            metadata=metadata,
        )

        chunks = self.chunker.chunk(input_data.text)
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

        self.repository.save_document(document)
        self.repository.save_chunks(doc_id, chunk_entities)

        return IngestDocumentOutput(
            document_id=doc_id,
            chunks_created=len(chunk_entities),
        )
