"""
===============================================================================
CRC — tests/unit/application/test_connector_source_use_cases.py

Responsibilities:
    - Validar CreateConnectorSourceUseCase (happy path, duplicado, ws inexistente).
    - Validar ListConnectorSourcesUseCase (happy path, ws inexistente).
    - Validar DeleteConnectorSourceUseCase (happy path, no encontrado, cross-ws).
    - Validar SyncConnectorSourceUseCase (stub devuelve NOT_IMPLEMENTED).

Collaborators:
    - FakeConnectorSourceRepository
    - FakeWorkspaceRepository (subset mínimo)
===============================================================================
"""

from __future__ import annotations

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
    ConnectorProvider,
    ConnectorSource,
    ConnectorSourceStatus,
)
from app.domain.entities import Workspace, WorkspaceVisibility

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
# SyncConnectorSourceUseCase (Stub)
# ===========================================================================


class TestSyncConnectorSourceStub:
    def test_returns_not_implemented(self, workspace, workspace_repo, connector_repo):
        create_uc = CreateConnectorSourceUseCase(
            connector_repo=connector_repo,
            workspace_repo=workspace_repo,
        )
        r = create_uc.execute(
            CreateConnectorSourceInput(workspace_id=workspace.id, folder_id="sync-test")
        )
        source_id = r.source.id

        sync_uc = SyncConnectorSourceUseCase(connector_repo=connector_repo)
        result = sync_uc.execute(workspace.id, source_id)
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_IMPLEMENTED

    def test_source_not_found(self, connector_repo):
        sync_uc = SyncConnectorSourceUseCase(connector_repo=connector_repo)
        result = sync_uc.execute(uuid4(), uuid4())
        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND
