"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/connectors.py
===============================================================================

Name:
    Connectors Router

Responsibilities:
    - Endpoints HTTP CRUD para connector sources (workspace-scoped).
    - Endpoints OAuth: start, callback, account status.
    - POST  /workspaces/{id}/connectors/google-drive/sources
    - GET   /workspaces/{id}/connectors/sources
    - DELETE /workspaces/{id}/connectors/sources/{source_id}
    - GET   /workspaces/{id}/connectors/google-drive/auth/start
    - GET   /workspaces/{id}/connectors/google-drive/auth/callback
    - GET   /workspaces/{id}/connectors/google-drive/account

Collaborators:
    - application.usecases.connectors.*
    - container factories
    - schemas.connectors
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from app.application.usecases.connectors import ConnectorErrorCode
from app.application.usecases.connectors.create_connector_source import (
    CreateConnectorSourceInput,
)
from app.application.usecases.connectors.handle_oauth_callback import (
    HandleOAuthCallbackInput,
)
from app.application.usecases.connectors.start_oauth import StartOAuthInput
from app.container import (
    get_connector_account_repository,
    get_create_connector_source_use_case,
    get_delete_connector_source_use_case,
    get_handle_oauth_callback_use_case,
    get_list_connector_sources_use_case,
    get_start_oauth_use_case,
    get_sync_connector_source_use_case,
)
from app.crosscutting.error_responses import (
    conflict,
    internal_error,
    not_found,
    validation_error,
)
from app.domain.connectors import ConnectorAccount, ConnectorProvider, ConnectorSource
from fastapi import APIRouter, Depends, Query, status

from ..schemas.connectors import (
    ConnectorAccountRes,
    ConnectorDeleteRes,
    ConnectorSourceListRes,
    ConnectorSourceRes,
    CreateConnectorSourceReq,
    StartOAuthRes,
    SyncStatsRes,
    SyncTriggerRes,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(source: ConnectorSource) -> ConnectorSourceRes:
    return ConnectorSourceRes(
        id=source.id,
        workspace_id=source.workspace_id,
        provider=source.provider.value,
        folder_id=source.folder_id,
        status=source.status.value,
        cursor_json=source.cursor_json,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def _to_account_response(account: ConnectorAccount) -> ConnectorAccountRes:
    return ConnectorAccountRes(
        id=account.id,
        workspace_id=account.workspace_id,
        provider=account.provider.value,
        account_email=account.account_email,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _raise_connector_error(error, *, workspace_id: UUID | None = None):
    """Traduce ConnectorError -> RFC7807."""
    if error.code == ConnectorErrorCode.VALIDATION_ERROR:
        raise validation_error(error.message)
    if error.code == ConnectorErrorCode.NOT_FOUND:
        raise not_found("ConnectorSource", str(workspace_id or "-"))
    if error.code == ConnectorErrorCode.CONFLICT:
        raise conflict(error.message)
    if error.code == ConnectorErrorCode.NOT_IMPLEMENTED:
        raise validation_error(error.message)
    raise internal_error(error.message)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/connectors/google-drive/sources",
    response_model=ConnectorSourceRes,
    status_code=status.HTTP_201_CREATED,
    tags=["connectors"],
    summary="Crear fuente Google Drive",
)
def create_google_drive_source(
    workspace_id: UUID,
    body: CreateConnectorSourceReq,
    use_case=Depends(get_create_connector_source_use_case),
):
    result = use_case.execute(
        CreateConnectorSourceInput(
            workspace_id=workspace_id,
            folder_id=body.folder_id,
        )
    )
    if result.error:
        _raise_connector_error(result.error, workspace_id=workspace_id)
    return _to_response(result.source)


@router.get(
    "/workspaces/{workspace_id}/connectors/sources",
    response_model=ConnectorSourceListRes,
    tags=["connectors"],
    summary="Listar fuentes de conectores",
)
def list_connector_sources(
    workspace_id: UUID,
    use_case=Depends(get_list_connector_sources_use_case),
):
    result = use_case.execute(workspace_id)
    if result.error:
        _raise_connector_error(result.error, workspace_id=workspace_id)
    sources = [_to_response(s) for s in result.sources]
    return ConnectorSourceListRes(sources=sources, count=len(sources))


@router.delete(
    "/workspaces/{workspace_id}/connectors/sources/{source_id}",
    response_model=ConnectorDeleteRes,
    tags=["connectors"],
    summary="Eliminar fuente de conector",
)
def delete_connector_source(
    workspace_id: UUID,
    source_id: UUID,
    use_case=Depends(get_delete_connector_source_use_case),
):
    result = use_case.execute(workspace_id, source_id)
    if result.error:
        _raise_connector_error(result.error, workspace_id=workspace_id)
    return ConnectorDeleteRes(deleted=result.deleted)


# ---------------------------------------------------------------------------
# OAuth endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/connectors/google-drive/auth/start",
    response_model=StartOAuthRes,
    tags=["connectors"],
    summary="Iniciar flujo OAuth Google Drive",
)
def start_oauth(
    workspace_id: UUID,
    use_case=Depends(get_start_oauth_use_case),
):
    result = use_case.execute(StartOAuthInput(workspace_id=workspace_id))
    if result.error:
        _raise_connector_error(result.error, workspace_id=workspace_id)
    return StartOAuthRes(authorization_url=result.authorization_url)


@router.get(
    "/workspaces/{workspace_id}/connectors/google-drive/auth/callback",
    response_model=ConnectorAccountRes,
    tags=["connectors"],
    summary="Callback OAuth Google Drive",
)
def oauth_callback(
    workspace_id: UUID,
    code: str = Query(..., description="Authorization code de Google"),
    state: str = Query(..., description="Estado OAuth (JSON)"),
    use_case=Depends(get_handle_oauth_callback_use_case),
    account_repo=Depends(get_connector_account_repository),
):
    result = use_case.execute(
        HandleOAuthCallbackInput(
            workspace_id=workspace_id,
            code=code,
            state=state,
        )
    )
    if result.error:
        _raise_connector_error(result.error, workspace_id=workspace_id)
    # Devolver la cuenta recién creada/actualizada
    gdrive_account = account_repo.get_by_workspace(
        workspace_id, ConnectorProvider.GOOGLE_DRIVE
    )
    if gdrive_account is None:
        raise internal_error("Account not found after OAuth callback")
    return _to_account_response(gdrive_account)


@router.get(
    "/workspaces/{workspace_id}/connectors/google-drive/account",
    response_model=ConnectorAccountRes,
    tags=["connectors"],
    summary="Estado de cuenta Google Drive vinculada",
)
def get_connector_account(
    workspace_id: UUID,
    account_repo=Depends(get_connector_account_repository),
):
    gdrive_account = account_repo.get_by_workspace(
        workspace_id, ConnectorProvider.GOOGLE_DRIVE
    )
    if gdrive_account is None:
        raise not_found("ConnectorAccount", str(workspace_id))
    return _to_account_response(gdrive_account)


# ---------------------------------------------------------------------------
# Sync trigger
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/connectors/sources/{source_id}/sync",
    response_model=SyncTriggerRes,
    tags=["connectors"],
    summary="Trigger sync de fuente de conector",
)
def trigger_sync(
    workspace_id: UUID,
    source_id: UUID,
    use_case=Depends(get_sync_connector_source_use_case),
):
    result = use_case.execute(workspace_id, source_id)
    if result.error:
        _raise_connector_error(result.error, workspace_id=workspace_id)
    return SyncTriggerRes(
        source_id=result.source_id,
        stats=SyncStatsRes(
            files_found=result.stats.files_found,
            files_ingested=result.stats.files_ingested,
            files_skipped=result.stats.files_skipped,
            files_errored=result.stats.files_errored,
        ),
    )
