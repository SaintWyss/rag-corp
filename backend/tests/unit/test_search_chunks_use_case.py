"""
Name: Search Chunks Use Case Unit Tests

Responsibilities:
  - Test SearchChunksUseCase orchestration logic
  - Verify embedding → retrieval flow
  - Test edge cases (zero top_k, no results)

Collaborators:
  - app.application.use_cases.search_chunks: Use case being tested
  - conftest: Mock fixtures for dependencies

Notes:
  - Uses mocks for all external dependencies
  - Fast execution (no DB, no API calls)
  - Mark with @pytest.mark.unit
"""

import pytest
from uuid import uuid4

from app.application.use_cases.search_chunks import (
    SearchChunksUseCase,
    SearchChunksInput,
)
from app.domain.entities import Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.users import UserRole


class _WorkspaceRepo:
    def __init__(self, workspace: Workspace):
        self._workspace = workspace

    def get_workspace(self, workspace_id):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


class _AclRepo:
    def list_workspace_acl(self, workspace_id):
        return []


_WORKSPACE = Workspace(
    id=uuid4(),
    name="Workspace",
    visibility=WorkspaceVisibility.PRIVATE,
)
_ACTOR = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)
_WORKSPACE_REPO = _WorkspaceRepo(_WORKSPACE)
_ACL_REPO = _AclRepo()


@pytest.mark.unit
class TestSearchChunksUseCase:
    """Test suite for SearchChunksUseCase."""

    def test_execute_returns_matching_chunks(
        self,
        mock_repository,
        mock_embedding_service,
        sample_chunks,
    ):
        """R: Should return chunks matching the query."""
        # Arrange
        query_embedding = [0.5] * 768
        mock_embedding_service.embed_query.return_value = query_embedding
        mock_repository.find_similar_chunks.return_value = sample_chunks

        use_case = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
        )

        input_data = SearchChunksInput(
            query="test query",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=3,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.error is None
        assert len(result.matches) == len(sample_chunks)
        mock_embedding_service.embed_query.assert_called_once_with("test query")
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=query_embedding,
            top_k=3,
            workspace_id=_WORKSPACE.id,
        )

    def test_execute_with_zero_top_k(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """R: Should return empty results when top_k is 0."""
        # Arrange
        use_case = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
        )

        input_data = SearchChunksInput(
            query="test",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=0,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.error is None
        assert result.matches == []
        mock_embedding_service.embed_query.assert_not_called()
        mock_repository.find_similar_chunks.assert_not_called()

    def test_execute_with_no_results(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """R: Should handle case when no chunks match."""
        # Arrange
        mock_embedding_service.embed_query.return_value = [0.1] * 768
        mock_repository.find_similar_chunks.return_value = []

        use_case = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
        )

        input_data = SearchChunksInput(
            query="nonexistent topic",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=5,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.error is None
        assert result.matches == []

    def test_execute_respects_top_k(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """R: Should pass top_k parameter to repository."""
        # Arrange
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = []

        use_case = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
        )

        # Act
        use_case.execute(
            SearchChunksInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=10,
            )
        )

        # Assert
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=[0.5] * 768,
            top_k=10,
            workspace_id=_WORKSPACE.id,
        )


@pytest.mark.unit
class TestSearchChunksInput:
    """Test suite for SearchChunksInput data class."""

    def test_create_with_defaults(self):
        """R: Should create input with default top_k=5."""
        input_data = SearchChunksInput(
            query="test query",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
        )

        assert input_data.query == "test query"
        assert input_data.top_k == 5

    def test_create_with_custom_top_k(self):
        """R: Should accept custom top_k value."""
        input_data = SearchChunksInput(
            query="test",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=20,
        )

        assert input_data.top_k == 20
