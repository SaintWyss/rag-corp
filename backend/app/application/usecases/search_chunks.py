"""
Name: Search Chunks Use Case

Responsibilities:
  - Orchestrate semantic search (embed query → retrieve chunks)
  - Coordinate repository and embedding service
  - Enforce workspace read access
  - Return matching chunks with similarity
"""

from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories import (
    DocumentRepository,
    WorkspaceRepository,
    WorkspaceAclRepository,
)
from ...domain.services import EmbeddingService
from ...domain.workspace_policy import WorkspaceActor
from .document_results import SearchChunksResult
from .workspace_access import resolve_workspace_for_read


@dataclass
class SearchChunksInput:
    query: str
    workspace_id: UUID
    actor: WorkspaceActor | None
    top_k: int = 5
    use_mmr: bool = False


class SearchChunksUseCase:
    """
    R: Use case for semantic search without generation.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
        embedding_service: EmbeddingService,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.acl_repository = acl_repository
        self.embedding_service = embedding_service

    def execute(self, input_data: SearchChunksInput) -> SearchChunksResult:
        _, error = resolve_workspace_for_read(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self.workspace_repository,
            acl_repository=self.acl_repository,
        )
        if error:
            return SearchChunksResult(matches=[], error=error)

        if input_data.top_k <= 0:
            return SearchChunksResult(matches=[])
        query_embedding = self.embedding_service.embed_query(input_data.query)
        if input_data.use_mmr:
            chunks = self.repository.find_similar_chunks_mmr(
                embedding=query_embedding,
                top_k=input_data.top_k,
                fetch_k=input_data.top_k * 4,
                lambda_mult=0.5,
                workspace_id=input_data.workspace_id,
            )
        else:
            chunks = self.repository.find_similar_chunks(
                embedding=query_embedding,
                top_k=input_data.top_k,
                workspace_id=input_data.workspace_id,
            )
        return SearchChunksResult(matches=chunks)
