"""
Name: Ingest Document Dedup Unit Tests

Responsibilities:
  - Verify duplicate text returns existing doc idempotently
  - Verify new text ingests normally with content_hash persisted
  - Verify empty text skips dedup lookup
  - Verify cross-workspace isolation (same text, different workspace)
  - Verify race condition recovery on UniqueViolation
"""

from __future__ import annotations

from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from app.application.content_hash import compute_content_hash
from app.application.usecases.documents.document_results import DocumentErrorCode
from app.application.usecases.ingestion.ingest_document import (
    IngestDocumentInput,
    IngestDocumentUseCase,
)
from app.domain.entities import Document, Workspace, WorkspaceVisibility
from app.domain.services import TextChunkerService
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

pytestmark = pytest.mark.unit

_WS_ID = UUID("00000000-0000-0000-0000-000000000001")
_WS_ID_2 = UUID("00000000-0000-0000-0000-000000000099")
_ACTOR = WorkspaceActor(
    user_id=UUID("00000000-0000-0000-0000-000000000002"),
    role=UserRole.ADMIN,
)


class _WorkspaceRepo:
    def __init__(self, *workspaces: Workspace):
        self._map = {ws.id: ws for ws in workspaces}

    def get_workspace(self, workspace_id: UUID):
        return self._map.get(workspace_id)


def _workspace(ws_id: UUID = _WS_ID) -> Workspace:
    return Workspace(
        id=ws_id,
        name="Test WS",
        visibility=WorkspaceVisibility.PRIVATE,
    )


def _existing_doc(ws_id: UUID = _WS_ID) -> Document:
    return Document(
        id=uuid4(),
        title="Existing Doc",
        workspace_id=ws_id,
        content_hash="abc123",
    )


def _build_use_case(
    mock_repo: Mock,
    mock_embedding: Mock,
    mock_chunker: Mock,
    *workspaces: Workspace,
) -> IngestDocumentUseCase:
    ws_repo = _WorkspaceRepo(*workspaces)
    return IngestDocumentUseCase(
        repository=mock_repo,
        workspace_repository=ws_repo,
        embedding_service=mock_embedding,
        chunker=mock_chunker,
    )


class TestIngestDedup:
    def test_duplicate_text_returns_existing_document(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """Duplicate content: should return existing doc without re-ingesting."""
        existing = _existing_doc()
        mock_repository.get_document_by_content_hash.return_value = existing

        chunker = Mock(spec=TextChunkerService)
        ws = _workspace()
        uc = _build_use_case(mock_repository, mock_embedding_service, chunker, ws)

        result = uc.execute(
            IngestDocumentInput(
                workspace_id=_WS_ID,
                actor=_ACTOR,
                title="Duplicate Doc",
                text="some text",
            )
        )

        assert result.error is None
        assert result.document_id == existing.id
        assert result.chunks_created == 0
        # Must NOT call embedding or save
        mock_embedding_service.embed_batch.assert_not_called()
        mock_repository.save_document_with_chunks.assert_not_called()

    def test_new_text_ingests_with_content_hash(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """New content: should ingest normally and persist content_hash."""
        mock_repository.get_document_by_content_hash.return_value = None

        chunker = Mock(spec=TextChunkerService)
        chunker.chunk.return_value = ["Chunk A"]
        mock_embedding_service.embed_batch.return_value = [[0.1] * 768]

        ws = _workspace()
        uc = _build_use_case(mock_repository, mock_embedding_service, chunker, ws)

        result = uc.execute(
            IngestDocumentInput(
                workspace_id=_WS_ID,
                actor=_ACTOR,
                title="New Doc",
                text="new content",
            )
        )

        assert result.error is None
        assert result.chunks_created == 1

        saved_doc = mock_repository.save_document_with_chunks.call_args[0][0]
        expected_hash = compute_content_hash(_WS_ID, "new content")
        assert saved_doc.content_hash == expected_hash

    def test_empty_text_skips_dedup_lookup(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """Empty text: should NOT call get_document_by_content_hash."""
        chunker = Mock(spec=TextChunkerService)
        chunker.chunk.return_value = []

        ws = _workspace()
        uc = _build_use_case(mock_repository, mock_embedding_service, chunker, ws)

        result = uc.execute(
            IngestDocumentInput(
                workspace_id=_WS_ID,
                actor=_ACTOR,
                title="Empty Doc",
                text="",
            )
        )

        assert result.error is None
        assert result.chunks_created == 0
        mock_repository.get_document_by_content_hash.assert_not_called()

    def test_cross_workspace_same_text_not_duplicate(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """Same text in different workspace: should NOT be considered duplicate."""
        mock_repository.get_document_by_content_hash.return_value = None

        chunker = Mock(spec=TextChunkerService)
        chunker.chunk.return_value = ["Chunk X"]
        mock_embedding_service.embed_batch.return_value = [[0.1] * 768]

        ws1 = _workspace(_WS_ID)
        ws2 = _workspace(_WS_ID_2)
        uc = _build_use_case(mock_repository, mock_embedding_service, chunker, ws1, ws2)

        text = "same content both workspaces"

        # Ingest into workspace 1
        r1 = uc.execute(
            IngestDocumentInput(
                workspace_id=_WS_ID,
                actor=_ACTOR,
                title="Doc WS1",
                text=text,
            )
        )
        # Ingest into workspace 2
        r2 = uc.execute(
            IngestDocumentInput(
                workspace_id=_WS_ID_2,
                actor=_ACTOR,
                title="Doc WS2",
                text=text,
            )
        )

        assert r1.error is None
        assert r2.error is None
        # Both should have ingested (different workspace scope)
        assert mock_repository.save_document_with_chunks.call_count == 2

        # Verify that the hash lookups used different workspace IDs
        calls = mock_repository.get_document_by_content_hash.call_args_list
        ws_ids_queried = {call[0][0] for call in calls}
        assert _WS_ID in ws_ids_queried
        assert _WS_ID_2 in ws_ids_queried

    def test_race_condition_returns_existing_on_save_failure(
        self,
        mock_repository,
        mock_embedding_service,
    ):
        """Race condition: save fails with unique violation, re-read returns existing."""
        mock_repository.get_document_by_content_hash.side_effect = [
            None,  # first call: no existing doc
            _existing_doc(),  # second call (race recovery): found existing
        ]

        chunker = Mock(spec=TextChunkerService)
        chunker.chunk.return_value = ["Chunk"]
        mock_embedding_service.embed_batch.return_value = [[0.1] * 768]

        mock_repository.save_document_with_chunks.side_effect = Exception(
            "UniqueViolation"
        )

        ws = _workspace()
        uc = _build_use_case(mock_repository, mock_embedding_service, chunker, ws)

        result = uc.execute(
            IngestDocumentInput(
                workspace_id=_WS_ID,
                actor=_ACTOR,
                title="Race Doc",
                text="race content",
            )
        )

        # Should recover gracefully
        assert result.error is None
        assert result.document_id is not None
        assert result.chunks_created == 0
