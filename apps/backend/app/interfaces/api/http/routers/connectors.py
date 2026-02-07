"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/connectors.py
===============================================================================

Name:
    Connectors Router

Responsibilities:
    - Endpoints HTTP CRUD para connector sources (workspace-scoped).
    - POST  /workspaces/{id}/connectors/google-drive/sources
    - GET   /workspaces/{id}/connectors/sources
    - DELETE /workspaces/{id}/connectors/sources/{source_id}

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
from app.container import (
    get_create_connector_source_use_case,
    get_delete_connector_source_use_case,
    get_list_connector_sources_use_case,
)
from app.crosscutting.error_responses import (
    conflict,
    internal_error,
    not_found,
    validation_error,
)
from app.domain.connectors import ConnectorSource
from fastapi import APIRouter, Depends, status

from ..schemas.connectors import (
    ConnectorDeleteRes,
    ConnectorSourceListRes,
    ConnectorSourceRes,
    CreateConnectorSourceReq,
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
