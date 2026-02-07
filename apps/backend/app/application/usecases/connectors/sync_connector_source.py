"""
===============================================================================
USE CASE: Sync Connector Source (Stub)
===============================================================================

Business Goal:
    Sincronizar archivos desde la fuente externa hacia el workspace.

    ** STUB: solo valida y loguea "not implemented". **
    La implementación real requiere OAuth + ConnectorClient.
===============================================================================
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.domain.connectors import ConnectorSourceRepository

from . import ConnectorError, ConnectorErrorCode, ConnectorSourceResult

logger = logging.getLogger(__name__)


class SyncConnectorSourceUseCase:
    """Stub de sincronización. No ejecuta sync real todavía."""

    def __init__(self, connector_repo: ConnectorSourceRepository):
        self._connector_repo = connector_repo

    def execute(self, workspace_id: UUID, source_id: UUID) -> ConnectorSourceResult:
        source = self._connector_repo.get(source_id)
        if source is None or source.workspace_id != workspace_id:
            return ConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Connector source {source_id} not found in workspace {workspace_id}",
                )
            )

        logger.info(
            "sync_connector_source: not implemented (stub)",
            extra={
                "source_id": str(source_id),
                "workspace_id": str(workspace_id),
                "provider": source.provider.value,
            },
        )

        return ConnectorSourceResult(
            error=ConnectorError(
                code=ConnectorErrorCode.NOT_IMPLEMENTED,
                message="Sync not implemented yet (OAuth required)",
            )
        )
