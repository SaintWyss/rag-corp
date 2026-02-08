"""
===============================================================================
CRC — tests/unit/application/test_connector_source_use_cases.py

Responsibilities:
    - Validar CreateConnectorSourceUseCase (happy path, duplicado, ws inexistente).
    - Validar ListConnectorSourcesUseCase (happy path, ws inexistente).
    - Validar DeleteConnectorSourceUseCase (happy path, no encontrado, cross-ws).
    - Validar SyncConnectorSourceUseCase (full implementation con fakes).
    - Validar sync update-aware: CREATE, UPDATE, SKIP_UNCHANGED scenarios.

Collaborators:
    - FakeConnectorSourceRepository
    - FakeWorkspaceRepository (subset mínimo)
    - FakeDocumentRepository (métodos update-aware)
===============================================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from app.application.usecases.connectors import ConnectorErrorCode
from app.application.usecases.connectors.create_connector_source import (
    CreateConnectorSourceInput,
    CreateConnectorSourceUseCase,
)
from app.application.usecases.connectors.delete_connector_source import (
    DeleteConnectorSourceUseCase,
)
from app.application.usecases.connectors.list_connector_sources import (
    ListConnectorSourcesUseCase,
)
from app.application.usecases.connectors.sync_connector_source import (
    SyncConnectorSourceUseCase,
)
from app.domain.connectors import (
    ConnectorAccount,
    ConnectorDelta,
    ConnectorFile,
    ConnectorProvider,
    ConnectorSource,
    ConnectorSourceStatus,
)
from app.domain.entities import Document, Workspace, WorkspaceVisibility

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeWorkspaceRepository:
    """Minimal workspace repo double for connector tests."""

    def __init__(self, workspaces: list[Workspace] | None = None):
        self._workspaces: dict[UUID, Workspace] = {
            ws.id: ws for ws in (workspaces or [])
        }

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return self._workspaces.get(workspace_id)


class FakeConnectorSourceRepository:
    """In-memory ConnectorSourceRepository for unit tests."""

    def __init__(self):
        self._sources: dict[UUID, ConnectorSource] = {}

    def create(self, source: ConnectorSource) -> None:
        self._sources[source.id] = source

    def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        provider: ConnectorProvider | None = None,
    ) -> List[ConnectorSource]:
        result = [s for s in self._sources.values() if s.workspace_id == workspace_id]
        if provider is not None:
            result = [s for s in result if s.provider == provider]
        return result

    def get(self, source_id: UUID) -> Optional[ConnectorSource]:
        return self._sources.get(source_id)

    def update_status(self, source_id: UUID, status: ConnectorSourceStatus) -> None:
        src = self._sources.get(source_id)
        if src:
            src.status = status

    def update_cursor(self, source_id: UUID, cursor_json: Dict[str, Any]) -> None:
        src = self._sources.get(source_id)
        if src:
            src.cursor_json = cursor_json

    def delete(self, source_id: UUID) -> bool:
        if source_id in self._sources:
            del self._sources[source_id]
            return True
        return False

    def try_set_syncing(self, source_id: UUID) -> bool:
        src = self._sources.get(source_id)
        if src is None:
            return False
        if src.status == ConnectorSourceStatus.SYNCING:
            return False
        src.status = ConnectorSourceStatus.SYNCING
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_workspace(workspace_id: UUID | None = None) -> Workspace:
    return Workspace(
        id=workspace_id or uuid4(),
        name="test-workspace",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=uuid4(),
    )


@pytest.fixture
def workspace() -> Workspace:
    return _make_workspace()


@pytest.fixture
def workspace_repo(workspace: Workspace) -> FakeWorkspaceRepository:
    return FakeWorkspaceRepository(workspaces=[workspace])


@pytest.fixture
def connector_repo() -> FakeConnectorSourceRepository:
    return FakeConnectorSourceRepository()


# ===========================================================================
# CreateConnectorSourceUseCase
# ===========================================================================


class TestCreateConnectorSource:
    def test_happy_path(self, workspace, workspace_repo, connector_repo):
        uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        result = uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id,
                folder_id="abc123",
            )
        )
        assert result.error is None
        assert result.source is not None
        assert result.source.workspace_id == workspace.id
        assert result.source.folder_id == "abc123"
        assert result.source.provider == ConnectorProvider.GOOGLE_DRIVE
        assert result.source.status == ConnectorSourceStatus.PENDING

    def test_empty_folder_id(self, workspace, workspace_repo, connector_repo):
        uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        result = uc.execute(
            CreateConnectorSourceInput(workspace_id=workspace.id, folder_id="  ")
        )
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.VALIDATION_ERROR

    def test_workspace_not_found(self, connector_repo):
        uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=FakeWorkspaceRepository(),
        )
        result = uc.execute(
            CreateConnectorSourceInput(workspace_id=uuid4(), folder_id="abc123")
        )
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND

    def test_duplicate_folder(self, workspace, workspace_repo, connector_repo):
        uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        # Primera creación OK
        r1 = uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="dup-folder"
            )
        )
        assert r1.error is None

        # Duplicado => CONFLICT
        r2 = uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="dup-folder"
            )
        )
        assert r2.error is not None
        assert r2.error.code == ConnectorErrorCode.CONFLICT

    def test_same_folder_different_workspace(self, connector_repo):
        ws1 = _make_workspace()
        ws2 = _make_workspace()
        ws_repo = FakeWorkspaceRepository(workspaces=[ws1, ws2])
        uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=ws_repo,
        )
        r1 = uc.execute(
            CreateConnectorSourceInput(workspace_id=ws1.id, folder_id="shared-folder")
        )
        r2 = uc.execute(
            CreateConnectorSourceInput(workspace_id=ws2.id, folder_id="shared-folder")
        )
        assert r1.error is None
        assert r2.error is None


# ===========================================================================
# ListConnectorSourcesUseCase
# ===========================================================================


class TestListConnectorSources:
    def test_empty_list(self, workspace, workspace_repo, connector_repo):
        uc = ListConnectorSourcesUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        result = uc.execute(workspace.id)
        assert result.error is None
        assert result.sources == []

    def test_returns_only_workspace_sources(self, connector_repo):
        ws1 = _make_workspace()
        ws2 = _make_workspace()
        ws_repo = FakeWorkspaceRepository(workspaces=[ws1, ws2])

        # Crear sources en ambos workspaces
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=ws_repo,
        )
        create_uc.execute(
            CreateConnectorSourceInput(workspace_id=ws1.id, folder_id="f1")
        )
        create_uc.execute(
            CreateConnectorSourceInput(workspace_id=ws2.id, folder_id="f2")
        )

        list_uc = ListConnectorSourcesUseCase(
            connector_repo=connector_repo,
            workspace_repo=ws_repo,
        )
        result = list_uc.execute(ws1.id)
        assert result.error is None
        assert len(result.sources) == 1
        assert result.sources[0].folder_id == "f1"

    def test_workspace_not_found(self, connector_repo):
        uc = ListConnectorSourcesUseCase(
            connector_repo=connector_repo,
            workspace_repo=FakeWorkspaceRepository(),
        )
        result = uc.execute(uuid4())
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND


# ===========================================================================
# DeleteConnectorSourceUseCase
# ===========================================================================


class TestDeleteConnectorSource:
    def test_happy_path(self, workspace, workspace_repo, connector_repo):
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=workspace.id, folder_id="to-delete")
        )
        source_id = r.source.id

        delete_uc = DeleteConnectorSourceUseCase(connector_repo=connector_repo)
        result = delete_uc.execute(workspace.id, source_id)
        assert result.error is None
        assert result.deleted is True

        # Verificar que fue eliminado
        assert connector_repo.get(source_id) is None

    def test_not_found(self, connector_repo):
        delete_uc = DeleteConnectorSourceUseCase(connector_repo=connector_repo)
        result = delete_uc.execute(uuid4(), uuid4())
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND

    def test_cross_workspace_rejection(self, connector_repo):
        """No permite eliminar un source que pertenece a otro workspace."""
        ws1 = _make_workspace()
        ws2 = _make_workspace()
        ws_repo = FakeWorkspaceRepository(workspaces=[ws1, ws2])

        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=ws_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=ws1.id, folder_id="owned-by-ws1")
        )
        source_id = r.source.id

        delete_uc = DeleteConnectorSourceUseCase(connector_repo=connector_repo)
        # Intentar borrar desde ws2
        result = delete_uc.execute(ws2.id, source_id)
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND

        # Source sigue existiendo
        assert connector_repo.get(source_id) is not None


# ===========================================================================
# SyncConnectorSourceUseCase (Full + Update-Aware)
# ===========================================================================


class FakeTokenEncryption:
    """Fake: prefija con 'ENC:' / lo quita al descifrar."""

    def encrypt(self, plaintext: str) -> str:
        return f"ENC:{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith("ENC:"):
            raise ValueError("bad ciphertext")
        return ciphertext[4:]


class FakeOAuthPort:
    """Fake OAuth port: refresh devuelve token fijo."""

    def __init__(self, *, refresh_error: str | None = None):
        self._refresh_error = refresh_error

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        return "https://fake"

    def exchange_code(self, *, code: str, redirect_uri: str):
        pass  # not used in sync

    def refresh_access_token(self, refresh_token: str) -> str:
        if self._refresh_error:
            raise ValueError(self._refresh_error)
        return "fresh-access-token"


class FakeConnectorAccountRepository:
    def __init__(self):
        self._data: dict[tuple[UUID, str], ConnectorAccount] = {}

    def upsert(self, account: ConnectorAccount) -> None:
        self._data[(account.workspace_id, account.provider.value)] = account

    def get_by_workspace(
        self, workspace_id: UUID, provider: ConnectorProvider
    ) -> ConnectorAccount | None:
        return self._data.get((workspace_id, provider.value))

    def delete(self, account_id: UUID) -> bool:
        return False


class FakeDocumentRepository:
    """In-memory document repo with update-aware support."""

    def __init__(self):
        self._docs: dict[UUID, Document] = {}
        self._chunks_deleted: list[UUID] = []
        self._nodes_deleted: list[UUID] = []

    def save_document(self, document: Document) -> None:
        self._docs[document.id] = document

    def get_by_external_source_id(
        self, workspace_id: UUID, external_source_id: str
    ) -> Document | None:
        for doc in self._docs.values():
            if (
                doc.workspace_id == workspace_id
                and doc.external_source_id == external_source_id
            ):
                return doc
        return None

    def delete_chunks_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        self._chunks_deleted.append(document_id)
        return 1

    def delete_nodes_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        self._nodes_deleted.append(document_id)
        return 1

    def update_external_source_metadata(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        external_source_provider: str | None = None,
        external_modified_time=None,
        external_etag: str | None = None,
        external_mime_type: str | None = None,
    ) -> bool:
        doc = self._docs.get(document_id)
        if doc is None:
            return False
        doc.external_source_provider = external_source_provider
        doc.external_modified_time = external_modified_time
        doc.external_etag = external_etag
        doc.external_mime_type = external_mime_type
        return True


class FakeDriveClient:
    """Fake Google Drive client."""

    def __init__(self, files: list[ConnectorFile] | None = None):
        self._files = files or []
        self._content: dict[str, bytes] = {}

    def set_content(self, file_id: str, content: bytes):
        self._content[file_id] = content

    def list_files(self, folder_id, *, page_token=None):
        return self._files

    def fetch_file_content(self, file_id, *, mime_type=""):
        import hashlib

        if file_id in self._content:
            data = self._content[file_id]
        else:
            data = b"file content for " + file_id.encode()
        sha = hashlib.sha256(data).hexdigest()
        return data, sha

    def get_delta(self, folder_id, *, cursor=None):
        return ConnectorDelta(
            files=self._files,
            new_cursor={"page_token": "next-cursor"},
        )

    @staticmethod
    def is_supported_mime(mime_type: str) -> bool:
        return mime_type in {
            "text/plain",
            "application/vnd.google-apps.document",
        }


def _make_sync_uc(
    workspace,
    connector_repo,
    workspace_repo,
    account_repo=None,
    document_repo=None,
    encryption=None,
    oauth_port=None,
    drive_client=None,
):
    """Helper para construir SyncConnectorSourceUseCase con fakes."""
    if account_repo is None:
        account_repo = FakeConnectorAccountRepository()
    if document_repo is None:
        document_repo = FakeDocumentRepository()
    if encryption is None:
        encryption = FakeTokenEncryption()
    if oauth_port is None:
        oauth_port = FakeOAuthPort()

    # Crear cuenta vinculada por defecto
    account = ConnectorAccount(
        id=uuid4(),
        workspace_id=workspace.id,
        provider=ConnectorProvider.GOOGLE_DRIVE,
        account_email="user@test.com",
        encrypted_refresh_token="ENC:refresh-token",
    )
    account_repo.upsert(account)

    return SyncConnectorSourceUseCase(
        connector_repo=connector_repo,
        account_repo=account_repo,
        document_repo=document_repo,
        encryption=encryption,
        oauth_port=oauth_port,
        drive_client_factory=lambda _token: drive_client or FakeDriveClient(),
    )


class TestSyncConnectorSource:
    """Tests para sync básico (CREATE flow)."""

    def test_happy_path(self, workspace, workspace_repo, connector_repo):
        """Sync ingests new files and updates cursor."""
        # Setup source
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="sync-folder"
            )
        )
        source_id = r.source.id

        files = [
            ConnectorFile(file_id="f1", name="doc1.txt", mime_type="text/plain"),
            ConnectorFile(
                file_id="f2",
                name="gdoc",
                mime_type="application/vnd.google-apps.document",
            ),
        ]
        client = FakeDriveClient(files=files)

        doc_repo = FakeDocumentRepository()
        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client,
        )
        result = sync_uc.execute(workspace.id, source_id)

        assert result.error is None
        assert result.stats.files_found == 2
        assert result.stats.files_ingested == 2
        assert result.stats.files_skipped == 0

        # Cursor updated
        src = connector_repo.get(source_id)
        assert src.cursor_json == {"page_token": "next-cursor"}
        assert src.status == ConnectorSourceStatus.ACTIVE

        # Documents persisted with external_source_id
        assert doc_repo.get_by_external_source_id(workspace.id, "gdrive:f1") is not None
        assert doc_repo.get_by_external_source_id(workspace.id, "gdrive:f2") is not None

    def test_unsupported_mime_skipped(self, workspace, workspace_repo, connector_repo):
        """Files with unsupported MIME types are skipped."""
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="mime-folder"
            )
        )
        source_id = r.source.id

        files = [
            ConnectorFile(file_id="f1", name="image.png", mime_type="image/png"),
        ]
        client = FakeDriveClient(files=files)

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            drive_client=client,
        )
        result = sync_uc.execute(workspace.id, source_id)
        assert result.stats.files_skipped == 1
        assert result.stats.files_ingested == 0

    def test_source_not_found(self, workspace, workspace_repo, connector_repo):
        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
        )
        result = sync_uc.execute(workspace.id, uuid4())
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND

    def test_no_account_connected(self, workspace, workspace_repo, connector_repo):
        """Sync fails if no OAuth account connected."""
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=workspace.id, folder_id="no-acc")
        )
        source_id = r.source.id

        empty_account_repo = FakeConnectorAccountRepository()
        sync_uc = SyncConnectorSourceUseCase(
            connector_repo=connector_repo,
            account_repo=empty_account_repo,
            document_repo=FakeDocumentRepository(),
            encryption=FakeTokenEncryption(),
            oauth_port=FakeOAuthPort(),
        )
        result = sync_uc.execute(workspace.id, source_id)
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.VALIDATION_ERROR
        assert "No Google Drive account" in result.error.message

    def test_token_refresh_failure(self, workspace, workspace_repo, connector_repo):
        """Sync fails and marks source ERROR if token refresh fails."""
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="refresh-fail"
            )
        )
        source_id = r.source.id

        oauth_port = FakeOAuthPort(refresh_error="token revoked")
        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            oauth_port=oauth_port,
        )
        result = sync_uc.execute(workspace.id, source_id)
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.VALIDATION_ERROR
        assert "token revoked" in result.error.message

        # Source should be marked ERROR
        src = connector_repo.get(source_id)
        assert src.status == ConnectorSourceStatus.ERROR


class TestSyncUpdateAware:
    """Tests para sync update-aware (UPDATE / SKIP_UNCHANGED flows)."""

    def test_idempotency_skips_unchanged(
        self, workspace, workspace_repo, connector_repo
    ):
        """
        Sync debe skipear archivos que no cambiaron.

        Scenario:
        1. Primer sync: archivo se crea con modified_time=T1.
        2. Segundo sync: mismo archivo con mismo modified_time=T1.
        3. Resultado: SKIP_UNCHANGED (no duplicado, no re-ingesta).
        """
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="idem-folder"
            )
        )
        source_id = r.source.id

        # Timestamp fijo
        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        files = [
            ConnectorFile(
                file_id="f1",
                name="doc1.txt",
                mime_type="text/plain",
                modified_time=fixed_time,
                etag="checksum123",
            ),
        ]
        client = FakeDriveClient(files=files)
        doc_repo = FakeDocumentRepository()

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client,
        )

        # First sync: should create
        r1 = sync_uc.execute(workspace.id, source_id)
        assert r1.stats.files_ingested == 1
        assert r1.stats.files_skipped == 0

        # Verificar que el documento tiene metadata externa
        created_doc = doc_repo.get_by_external_source_id(workspace.id, "gdrive:f1")
        assert created_doc is not None
        assert created_doc.external_source_provider == "google_drive"
        assert created_doc.external_modified_time == fixed_time
        assert created_doc.external_etag == "checksum123"

        # Second sync: same file, same metadata → SKIP_UNCHANGED
        r2 = sync_uc.execute(workspace.id, source_id)
        assert r2.stats.files_ingested == 0
        assert r2.stats.files_skipped == 1
        assert r2.stats.files_updated == 0

    def test_update_when_modified_time_changed(
        self, workspace, workspace_repo, connector_repo
    ):
        """
        Sync debe actualizar (UPDATE) si modified_time cambió.

        Scenario:
        1. Primer sync: archivo con modified_time=T1.
        2. Segundo sync: mismo file_id pero modified_time=T2 (>T1).
        3. Resultado: UPDATE (re-ingesta, chunks borrados, metadata actualizada).
        """
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="update-folder"
            )
        )
        source_id = r.source.id

        time_v1 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_v2 = datetime(2024, 1, 16, 14, 30, 0, tzinfo=timezone.utc)

        doc_repo = FakeDocumentRepository()

        # First sync: create with T1
        files_v1 = [
            ConnectorFile(
                file_id="f1",
                name="report.txt",
                mime_type="text/plain",
                modified_time=time_v1,
            ),
        ]
        client_v1 = FakeDriveClient(files=files_v1)

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client_v1,
        )

        r1 = sync_uc.execute(workspace.id, source_id)
        assert r1.stats.files_ingested == 1
        created_doc = doc_repo.get_by_external_source_id(workspace.id, "gdrive:f1")
        original_doc_id = created_doc.id
        assert created_doc.external_modified_time == time_v1

        # Second sync: update with T2 (changed)
        files_v2 = [
            ConnectorFile(
                file_id="f1",
                name="report.txt",
                mime_type="text/plain",
                modified_time=time_v2,  # Changed!
            ),
        ]
        client_v2 = FakeDriveClient(files=files_v2)

        sync_uc2 = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client_v2,
        )

        r2 = sync_uc2.execute(workspace.id, source_id)
        assert r2.stats.files_ingested == 0
        assert r2.stats.files_updated == 1
        assert r2.stats.files_skipped == 0

        # Verificar que el documento se actualizó (mismo ID, nueva metadata)
        updated_doc = doc_repo.get_by_external_source_id(workspace.id, "gdrive:f1")
        assert updated_doc.id == original_doc_id  # Same document ID
        assert updated_doc.external_modified_time == time_v2  # Updated metadata

        # Verificar que se borraron los chunks
        assert original_doc_id in doc_repo._chunks_deleted

    def test_update_when_etag_changed(self, workspace, workspace_repo, connector_repo):
        """
        Sync debe actualizar (UPDATE) si etag cambió (incluso si modified_time igual).

        Scenario:
        1. Primer sync: archivo con etag=ABC.
        2. Segundo sync: mismo file_id pero etag=XYZ.
        3. Resultado: UPDATE.
        """
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="etag-folder"
            )
        )
        source_id = r.source.id

        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        doc_repo = FakeDocumentRepository()

        # First sync: etag ABC
        files_v1 = [
            ConnectorFile(
                file_id="f1",
                name="config.txt",
                mime_type="text/plain",
                modified_time=fixed_time,
                etag="md5-ABC",
            ),
        ]
        client_v1 = FakeDriveClient(files=files_v1)

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client_v1,
        )

        r1 = sync_uc.execute(workspace.id, source_id)
        assert r1.stats.files_ingested == 1

        # Second sync: etag changed to XYZ
        files_v2 = [
            ConnectorFile(
                file_id="f1",
                name="config.txt",
                mime_type="text/plain",
                modified_time=fixed_time,  # Same time
                etag="md5-XYZ",  # Different etag!
            ),
        ]
        client_v2 = FakeDriveClient(files=files_v2)

        sync_uc2 = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client_v2,
        )

        r2 = sync_uc2.execute(workspace.id, source_id)
        assert r2.stats.files_updated == 1
        assert r2.stats.files_skipped == 0

    def test_cross_workspace_isolation(self, connector_repo):
        """
        Documentos de un workspace no deben afectar sync de otro workspace.

        Scenario:
        1. ws1 sincroniza archivo f1 → crea doc.
        2. ws2 sincroniza mismo archivo f1 → debe crear nuevo doc (no encontrar el de ws1).
        """
        ws1 = _make_workspace()
        ws2 = _make_workspace()
        ws_repo = FakeWorkspaceRepository(workspaces=[ws1, ws2])

        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=ws_repo,
        )

        # Create sources in both workspaces
        r1 = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=ws1.id, folder_id="shared-drive")
        )
        r2 = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=ws2.id, folder_id="shared-drive")
        )
        source_id_1 = r1.source.id
        source_id_2 = r2.source.id

        # Same file in both syncs
        files = [
            ConnectorFile(
                file_id="shared-f1",
                name="shared.txt",
                mime_type="text/plain",
            ),
        ]
        client = FakeDriveClient(files=files)
        doc_repo = FakeDocumentRepository()

        # Sync ws1
        sync_uc1 = _make_sync_uc(
            ws1,
            connector_repo,
            ws_repo,
            document_repo=doc_repo,
            drive_client=client,
        )
        result1 = sync_uc1.execute(ws1.id, source_id_1)
        assert result1.stats.files_ingested == 1  # Created in ws1

        # Sync ws2: should also CREATE (not find ws1's document)
        sync_uc2 = _make_sync_uc(
            ws2,
            connector_repo,
            ws_repo,
            document_repo=doc_repo,
            drive_client=client,
        )
        result2 = sync_uc2.execute(ws2.id, source_id_2)
        assert result2.stats.files_ingested == 1  # Created in ws2

        # Verify both workspaces have their own document
        doc_ws1 = doc_repo.get_by_external_source_id(ws1.id, "gdrive:shared-f1")
        doc_ws2 = doc_repo.get_by_external_source_id(ws2.id, "gdrive:shared-f1")
        assert doc_ws1 is not None
        assert doc_ws2 is not None
        assert doc_ws1.id != doc_ws2.id  # Different documents

    def test_external_metadata_persisted_on_create(
        self, workspace, workspace_repo, connector_repo
    ):
        """
        Al crear un documento, la metadata externa debe persistirse correctamente.
        """
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="meta-folder"
            )
        )
        source_id = r.source.id

        file_time = datetime(2024, 6, 20, 10, 30, 0, tzinfo=timezone.utc)
        files = [
            ConnectorFile(
                file_id="meta-f1",
                name="metadata-test.txt",
                mime_type="text/plain",
                modified_time=file_time,
                etag="md5-hash-123",
            ),
        ]
        client = FakeDriveClient(files=files)
        doc_repo = FakeDocumentRepository()

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client,
        )

        sync_uc.execute(workspace.id, source_id)

        doc = doc_repo.get_by_external_source_id(workspace.id, "gdrive:meta-f1")
        assert doc is not None
        assert doc.external_source_id == "gdrive:meta-f1"
        assert doc.external_source_provider == "google_drive"
        assert doc.external_modified_time == file_time
        assert doc.external_etag == "md5-hash-123"
        assert doc.external_mime_type == "text/plain"


# ===========================================================================
# Hardening P0: Sync Lock
# ===========================================================================


class TestSyncLock:
    """Tests para per-source sync lock (CAS status-based)."""

    def test_concurrent_sync_skipped(self, workspace, workspace_repo, connector_repo):
        """
        Si un source ya está en SYNCING, el segundo sync debe
        ser rechazado sin duplicar procesamiento.
        """
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="lock-folder"
            )
        )
        source_id = r.source.id

        # Marcar como SYNCING manualmente (simula sync en curso)
        connector_repo.update_status(source_id, ConnectorSourceStatus.SYNCING)

        files = [
            ConnectorFile(file_id="f1", name="doc.txt", mime_type="text/plain"),
        ]
        client = FakeDriveClient(files=files)

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            drive_client=client,
        )
        result = sync_uc.execute(workspace.id, source_id)

        # Debe skip sin error (stats vacías, no procesó nada)
        assert result.error is None
        assert result.stats is not None
        assert result.stats.files_found == 0
        assert result.stats.files_ingested == 0

    def test_sync_lock_released_on_success(
        self, workspace, workspace_repo, connector_repo
    ):
        """
        Post-sync el status debe volver a ACTIVE (lock liberado).
        """
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="release-folder"
            )
        )
        source_id = r.source.id

        files = [
            ConnectorFile(file_id="f1", name="doc.txt", mime_type="text/plain"),
        ]
        client = FakeDriveClient(files=files)

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            drive_client=client,
        )
        result = sync_uc.execute(workspace.id, source_id)

        assert result.error is None
        src = connector_repo.get(source_id)
        assert src.status == ConnectorSourceStatus.ACTIVE


# ===========================================================================
# Hardening P0: File Too Large (vía FakeDriveClient que lanza exc)
# ===========================================================================


class FakeDriveClientFileTooLarge(FakeDriveClient):
    """Drive client que lanza ConnectorFileTooLargeError para archivos específicos."""

    def __init__(self, files, *, too_large_ids: set[str] | None = None):
        super().__init__(files=files)
        self._too_large_ids = too_large_ids or set()

    def fetch_file_content(self, file_id, *, mime_type=""):
        from app.infrastructure.services.google_drive_client import (
            ConnectorFileTooLargeError,
        )

        if file_id in self._too_large_ids:
            raise ConnectorFileTooLargeError(
                file_id=file_id,
                size_bytes=100 * 1024 * 1024,
                max_bytes=25 * 1024 * 1024,
            )
        return super().fetch_file_content(file_id, mime_type=mime_type)


class TestFileTooLarge:
    """Tests para max file size guard."""

    def test_oversized_file_skipped(self, workspace, workspace_repo, connector_repo):
        """Archivos demasiado grandes deben skippearse sin error fatal."""
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="big-folder"
            )
        )
        source_id = r.source.id

        files = [
            ConnectorFile(file_id="big", name="huge.pdf", mime_type="text/plain"),
            ConnectorFile(file_id="small", name="tiny.txt", mime_type="text/plain"),
        ]
        client = FakeDriveClientFileTooLarge(files=files, too_large_ids={"big"})
        doc_repo = FakeDocumentRepository()

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client,
        )
        result = sync_uc.execute(workspace.id, source_id)

        # big → skipped, small → created
        assert result.stats.files_ingested == 1
        assert result.stats.files_skipped == 1
        assert result.error is None

        # Solo small fue persistido
        assert (
            doc_repo.get_by_external_source_id(workspace.id, "gdrive:small") is not None
        )
        assert doc_repo.get_by_external_source_id(workspace.id, "gdrive:big") is None

    def test_all_files_oversized_still_active(
        self, workspace, workspace_repo, connector_repo
    ):
        """Si todos los archivos son demasiado grandes, status final = ACTIVE."""
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=workspace.id, folder_id="all-big")
        )
        source_id = r.source.id

        files = [
            ConnectorFile(file_id="b1", name="big1.txt", mime_type="text/plain"),
        ]
        client = FakeDriveClientFileTooLarge(files=files, too_large_ids={"b1"})

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            drive_client=client,
        )
        result = sync_uc.execute(workspace.id, source_id)
        assert result.error is None
        src = connector_repo.get(source_id)
        assert src.status == ConnectorSourceStatus.ACTIVE


# ===========================================================================
# Hardening P0: Content hash persisted
# ===========================================================================


class TestContentHash:
    """Tests para hashing SHA-256 incremental integrado en sync."""

    def test_content_hash_stored_on_create(
        self, workspace, workspace_repo, connector_repo
    ):
        """El content_hash SHA-256 debe guardarse en el documento creado."""
        import hashlib

        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(
                workspace_id=workspace.id, folder_id="hash-folder"
            )
        )
        source_id = r.source.id

        content = b"deterministic content"
        expected_hash = hashlib.sha256(content).hexdigest()

        files = [
            ConnectorFile(file_id="hf1", name="hash.txt", mime_type="text/plain"),
        ]
        client = FakeDriveClient(files=files)
        client.set_content("hf1", content)
        doc_repo = FakeDocumentRepository()

        sync_uc = _make_sync_uc(
            workspace,
            connector_repo,
            workspace_repo,
            document_repo=doc_repo,
            drive_client=client,
        )
        sync_uc.execute(workspace.id, source_id)

        doc = doc_repo.get_by_external_source_id(workspace.id, "gdrive:hf1")
        assert doc is not None
        assert doc.content_hash == expected_hash
