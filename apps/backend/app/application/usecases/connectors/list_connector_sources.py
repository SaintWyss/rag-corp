"""
===============================================================================
USE CASE: List Connector Sources
===============================================================================

Business Goal:
    Listar las fuentes de conectores de un workspace.

Inputs:
    - workspace_id: UUID del workspace

Outputs:
    - ConnectorSourceListResult (sources | error)
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from app.domain.connectors import ConnectorSourceRepository
from app.domain.repositories import WorkspaceRepository

from . import ConnectorError, ConnectorErrorCode, ConnectorSourceListResult


class ListConnectorSourcesUseCase:
    """Lista los ConnectorSource de un workspace."""

    def __init__(
        self,
        connector_repo: ConnectorSourceRepository,
        workspace_repo: WorkspaceRepository,
    ):
        self._connector_repo = connector_repo
        self._workspace_repo = workspace_repo

    def execute(self, workspace_id: UUID) -> ConnectorSourceListResult:
        # Verificar que el workspace existe
        workspace = self._workspace_repo.get_workspace(workspace_id)
        if workspace is None:
            return ConnectorSourceListResult(
                sources=[],
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Workspace {workspace_id} not found",
                ),
            )

        sources = self._connector_repo.list_by_workspace(workspace_id)
        return ConnectorSourceListResult(sources=sources)
