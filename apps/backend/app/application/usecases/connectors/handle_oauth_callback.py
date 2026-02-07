"""
===============================================================================
USE CASE: Handle OAuth Callback
===============================================================================

Business Goal:
    Recibir el authorization code del proveedor OAuth, intercambiar por tokens,
    cifrar el refresh_token y persistir la cuenta vinculada.
===============================================================================
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.connectors import (
    ConnectorAccount,
    ConnectorAccountRepository,
    ConnectorProvider,
    OAuthPort,
    TokenEncryptionPort,
)
from app.domain.repositories import WorkspaceRepository

from . import ConnectorError, ConnectorErrorCode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HandleOAuthCallbackInput:
    workspace_id: UUID
    code: str
    state: str


@dataclass
class HandleOAuthCallbackResult:
    account_email: str | None = None
    error: ConnectorError | None = None


class HandleOAuthCallbackUseCase:
    """Procesa el callback OAuth: exchange code + persist tokens cifrados."""

    def __init__(
        self,
        oauth_port: OAuthPort,
        account_repo: ConnectorAccountRepository,
        workspace_repo: WorkspaceRepository,
        encryption: TokenEncryptionPort,
        redirect_uri_template: str,
    ):
        self._oauth = oauth_port
        self._account_repo = account_repo
        self._workspace_repo = workspace_repo
        self._encryption = encryption
        self._redirect_uri_template = redirect_uri_template

    def execute(  # noqa: C901
        self, input: HandleOAuthCallbackInput
    ) -> HandleOAuthCallbackResult:
        # 1) Validar state
        try:
            state_data = json.loads(input.state)
            state_workspace_id = state_data.get("workspace_id")
            if state_workspace_id != str(input.workspace_id):
                return HandleOAuthCallbackResult(
                    error=ConnectorError(
                        code=ConnectorErrorCode.VALIDATION_ERROR,
                        message="OAuth state workspace_id mismatch",
                    )
                )
        except (json.JSONDecodeError, KeyError):
            return HandleOAuthCallbackResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message="Invalid OAuth state",
                )
            )

        # 2) Verificar workspace
        workspace = self._workspace_repo.get_workspace(input.workspace_id)
        if workspace is None:
            return HandleOAuthCallbackResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Workspace {input.workspace_id} not found",
                )
            )

        # 3) Exchange code for tokens
        redirect_uri = self._redirect_uri_template.replace(
            "{workspace_id}", str(input.workspace_id)
        )
        try:
            token_response = self._oauth.exchange_code(
                code=input.code,
                redirect_uri=redirect_uri,
            )
        except ValueError as exc:
            logger.error(
                "oauth exchange failed",
                extra={"workspace_id": str(input.workspace_id), "error": str(exc)},
            )
            return HandleOAuthCallbackResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message=str(exc),
                )
            )

        # 4) Cifrar refresh_token y persistir
        encrypted_token = self._encryption.encrypt(token_response.refresh_token)

        account = ConnectorAccount(
            id=uuid4(),
            workspace_id=input.workspace_id,
            provider=ConnectorProvider.GOOGLE_DRIVE,
            account_email=token_response.email,
            encrypted_refresh_token=encrypted_token,
        )
        self._account_repo.upsert(account)

        # 5) Audit log (best-effort, sin PII innecesaria)
        logger.info(
            "connector_account_connected",
            extra={
                "workspace_id": str(input.workspace_id),
                "provider": ConnectorProvider.GOOGLE_DRIVE.value,
                "email_domain": (
                    token_response.email.split("@")[-1]
                    if "@" in token_response.email
                    else "unknown"
                ),
            },
        )

        return HandleOAuthCallbackResult(account_email=token_response.email)
