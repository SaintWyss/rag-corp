"""
===============================================================================
USE CASE: Start Google Drive OAuth
===============================================================================

Business Goal:
    Iniciar el flujo OAuth para vincular una cuenta de Google Drive a un workspace.
    Devuelve la URL de autorización a la que el frontend debe redirigir al usuario.
===============================================================================
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from app.domain.connectors import ConnectorProvider, OAuthPort
from app.domain.repositories import WorkspaceRepository

from . import ConnectorError, ConnectorErrorCode


@dataclass(frozen=True)
class StartOAuthInput:
    workspace_id: UUID


@dataclass
class StartOAuthResult:
    authorization_url: str | None = None
    error: ConnectorError | None = None


class StartOAuthUseCase:
    """Genera la URL de autorización OAuth para vincular Google Drive."""

    def __init__(
        self,
        oauth_port: OAuthPort,
        workspace_repo: WorkspaceRepository,
        redirect_uri_template: str,
    ):
        self._oauth = oauth_port
        self._workspace_repo = workspace_repo
        self._redirect_uri_template = redirect_uri_template

    def execute(self, input: StartOAuthInput) -> StartOAuthResult:
        # 1) Verificar workspace
        workspace = self._workspace_repo.get_workspace(input.workspace_id)
        if workspace is None:
            return StartOAuthResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Workspace {input.workspace_id} not found",
                )
            )

        # 2) Construir redirect_uri con workspace_id
        redirect_uri = self._redirect_uri_template.replace(
            "{workspace_id}", str(input.workspace_id)
        )

        # 3) State = JSON con workspace_id + provider (para validar en callback)
        state = json.dumps(
            {
                "workspace_id": str(input.workspace_id),
                "provider": ConnectorProvider.GOOGLE_DRIVE.value,
            }
        )

        # 4) Construir URL
        url = self._oauth.build_authorization_url(
            state=state,
            redirect_uri=redirect_uri,
        )

        return StartOAuthResult(authorization_url=url)
