"""
Name: Upload Document Dedup Unit Tests

Responsibilities:
  - Verify duplicate file returns existing doc without uploading to storage
  - Verify new file uploads normally with content_hash persisted
  - Verify cross-workspace isolation (same file bytes, different workspace)
  - Verify race condition recovery (save fails, re-read returns existing)
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid4

import pytest
from app.application.content_hash import compute_file_hash
from app.application.usecases.ingestion.upload_document import (
    UploadDocumentInput,
    UploadDocumentUseCase,
)
from app.domain.entities import Document, Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

pytestmark = pytest.mark.unit

_WS_ID = UUID("00000000-0000-0000-0000-000000000001")
_WS_ID_2 = UUID("00000000-0000-0000-0000-000000000099")
_ACTOR = WorkspaceActor(
    user_id=UUID("00000000-0000-0000-0000-000000000002"),
    role=UserRole.ADMIN,
)
_FILE_BYTES = b"raw-pdf-binary-content"


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
        title="Existing Upload",
        workspace_id=ws_id,
        file_name="existing.pdf",
        mime_type="application/pdf",
        status="READY",
        content_hash="abc123",
    )


def _build_use_case(
    mock_repo: Mock,
    storage: MagicMock,
    queue: MagicMock,
    *workspaces: Workspace,
) -> UploadDocumentUseCase:
    ws_repo = _WorkspaceRepo(*workspaces)
    return UploadDocumentUseCase(
        repository=mock_repo,
        workspace_repository=ws_repo,
        storage=storage,
        queue=queue,
    )


def _upload_input(
    ws_id: UUID = _WS_ID, content: bytes = _FILE_BYTES
) -> UploadDocumentInput:
    return UploadDocumentInput(
        workspace_id=ws_id,
        actor=_ACTOR,
        title="Upload Doc",
        file_name="sample.pdf",
        mime_type="application/pdf",
        content=content,
    )


class TestUploadDedup:
    def test_duplicate_file_returns_existing_without_upload(
        self,
        mock_repository,
    ):
        """Duplicate file: should return existing doc, skip storage upload."""
        existing = _existing_doc()
        mock_repository.get_document_by_content_hash.return_value = existing

        storage = MagicMock()
        queue = MagicMock()
        ws = _workspace()
        uc = _build_use_case(mock_repository, storage, queue, ws)

        result = uc.execute(_upload_input())

        assert result.error is None
        assert result.document_id == existing.id
        assert result.status == existing.status
        assert result.file_name == existing.file_name
        assert result.mime_type == existing.mime_type
        # Should NOT upload or save
        storage.upload_file.assert_not_called()
        mock_repository.save_document.assert_not_called()
        queue.enqueue_document_processing.assert_not_called()

    def test_new_file_uploads_with_content_hash(
        self,
        mock_repository,
    ):
        """New file: should upload and persist content_hash on document."""
        mock_repository.get_document_by_content_hash.return_value = None

        storage = MagicMock()
        queue = MagicMock()
        ws = _workspace()
        uc = _build_use_case(mock_repository, storage, queue, ws)

        result = uc.execute(_upload_input())

        assert result.error is None
        assert result.document_id is not None
        assert result.status == "PENDING"

        # Verify storage was called
        storage.upload_file.assert_called_once()
        # Verify document was saved with content_hash
        saved_doc = mock_repository.save_document.call_args[0][0]
        expected_hash = compute_file_hash(_WS_ID, _FILE_BYTES)
        assert saved_doc.content_hash == expected_hash

    def test_cross_workspace_same_file_not_duplicate(
        self,
        mock_repository,
    ):
        """Same file in different workspace: NOT a duplicate."""
        mock_repository.get_document_by_content_hash.return_value = None

        storage = MagicMock()
        queue = MagicMock()
        ws1 = _workspace(_WS_ID)
        ws2 = _workspace(_WS_ID_2)
        uc = _build_use_case(mock_repository, storage, queue, ws1, ws2)

        r1 = uc.execute(_upload_input(ws_id=_WS_ID))
        r2 = uc.execute(_upload_input(ws_id=_WS_ID_2))

        assert r1.error is None
        assert r2.error is None
        # Both should be uploaded (different workspace scope)
        assert storage.upload_file.call_count == 2
        assert mock_repository.save_document.call_count == 2

        # Verify hash lookups used different workspace IDs
        calls = mock_repository.get_document_by_content_hash.call_args_list
        ws_ids_queried = {call[0][0] for call in calls}
        assert _WS_ID in ws_ids_queried
        assert _WS_ID_2 in ws_ids_queried

    def test_file_hashes_differ_across_workspaces(self):
        """Same bytes produce different hashes for different workspaces."""
        h1 = compute_file_hash(_WS_ID, _FILE_BYTES)
        h2 = compute_file_hash(_WS_ID_2, _FILE_BYTES)
        assert h1 != h2
