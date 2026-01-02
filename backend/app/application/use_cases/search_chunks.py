"""
Name: Search Chunks Use Case

Responsibilities:
  - Orchestrate semantic search (embed query → retrieve chunks)
  - Coordinate repository and embedding service
  - Return matching chunks with similarity
"""

from dataclasses import dataclass
from typing import List

from ...domain.entities import Chunk
from ...domain.repositories import DocumentRepository
from ...domain.services import EmbeddingService


@dataclass
class SearchChunksInput:
    query: str
    top_k: int = 5


@dataclass
class SearchChunksOutput:
    matches: List[Chunk]


class SearchChunksUseCase:
    """
    R: Use case for semantic search without generation.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
    ):
        self.repository = repository
        self.embedding_service = embedding_service

    def execute(self, input_data: SearchChunksInput) -> SearchChunksOutput:
        if input_data.top_k <= 0:
            return SearchChunksOutput(matches=[])
        query_embedding = self.embedding_service.embed_query(input_data.query)
        chunks = self.repository.find_similar_chunks(
            embedding=query_embedding,
            top_k=input_data.top_k,
        )
        return SearchChunksOutput(matches=chunks)
