"""
===============================================================================
USE CASE: Delete Connector Source
===============================================================================

Business Goal:
    Eliminar una fuente de conector de un workspace.

Inputs:
    - workspace_id: UUID del workspace (para scoping)
    - source_id: UUID del ConnectorSource

Outputs:
    - ConnectorDeleteResult (deleted | error)
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from app.domain.connectors import ConnectorSourceRepository

from . import ConnectorDeleteResult, ConnectorError, ConnectorErrorCode


class DeleteConnectorSourceUseCase:
    """Elimina un ConnectorSource verificando workspace scoping."""

    def __init__(self, connector_repo: ConnectorSourceRepository):
        self._connector_repo = connector_repo

    def execute(self, workspace_id: UUID, source_id: UUID) -> ConnectorDeleteResult:
        # Verificar que existe y pertenece al workspace
        source = self._connector_repo.get(source_id)
        if source is None or source.workspace_id != workspace_id:
            return ConnectorDeleteResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Connector source {source_id} not found in workspace {workspace_id}",
                )
            )

        deleted = self._connector_repo.delete(source_id)
        return ConnectorDeleteResult(deleted=deleted)
