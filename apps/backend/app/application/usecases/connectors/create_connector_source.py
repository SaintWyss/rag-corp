"""
===============================================================================
USE CASE: Create Connector Source
===============================================================================

Business Goal:
    Registrar una nueva fuente Google Drive (carpeta) en un workspace.

Inputs:
    - workspace_id: UUID del workspace destino
    - folder_id: ID de la carpeta de Google Drive

Outputs:
    - ConnectorSourceResult (source | error)
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.connectors import (
    ConnectorProvider,
    ConnectorSource,
    ConnectorSourceRepository,
    ConnectorSourceStatus,
)
from app.domain.repositories import WorkspaceRepository

from . import ConnectorError, ConnectorErrorCode, ConnectorSourceResult


@dataclass(frozen=True)
class CreateConnectorSourceInput:
    workspace_id: UUID
    folder_id: str


class CreateConnectorSourceUseCase:
    """Crea un ConnectorSource (Google Drive) en el workspace indicado."""

    def __init__(
        self,
        connector_repo: ConnectorSourceRepository,
        workspace_repo: WorkspaceRepository,
    ):
        self._connector_repo = connector_repo
        self._workspace_repo = workspace_repo

    def execute(self, input: CreateConnectorSourceInput) -> ConnectorSourceResult:
        # 1) Validar input
        folder_id = (input.folder_id or "").strip()
        if not folder_id:
            return ConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message="folder_id is required",
                )
            )

        # 2) Verificar que el workspace existe
        workspace = self._workspace_repo.get_workspace(input.workspace_id)
        if workspace is None:
            return ConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Workspace {input.workspace_id} not found",
                )
            )

        # 3) Verificar unicidad (workspace + provider + folder_id)
        existing = self._connector_repo.list_by_workspace(
            input.workspace_id, provider=ConnectorProvider.GOOGLE_DRIVE
        )
        for src in existing:
            if src.folder_id == folder_id:
                return ConnectorSourceResult(
                    error=ConnectorError(
                        code=ConnectorErrorCode.CONFLICT,
                        message=f"Folder '{folder_id}' already connected to this workspace",
                    )
                )

        # 4) Crear entidad y persistir
        source = ConnectorSource(
            id=uuid4(),
            workspace_id=input.workspace_id,
            provider=ConnectorProvider.GOOGLE_DRIVE,
            folder_id=folder_id,
            status=ConnectorSourceStatus.PENDING,
        )
        self._connector_repo.create(source)

        return ConnectorSourceResult(source=source)
