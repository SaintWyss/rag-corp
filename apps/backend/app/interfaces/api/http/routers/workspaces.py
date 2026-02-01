"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/workspaces.py
===============================================================================

Class/Module:
    Workspace Router

Responsibilities:
    - Exponer endpoints HTTP para la administración y consulta de Workspaces.
    - Convertir requests HTTP -> inputs de casos de uso.
    - Traducir WorkspaceError -> RFC7807.
    - Enforce de auth/permisos/roles en el borde (capa HTTP).
    - Registrar auditoría (best-effort).

Collaborators:
    - app.application.usecases (Create/Update/Get/List/Publish/Share/Archive)
    - app.identity.dual_auth (require_principal, require_admin, require_employee_or_admin)
    - app.identity.rbac.Permission
    - app.audit.emit_audit_event
    - app.container (factories DI)
    - schemas.workspaces (DTOs Pydantic)

Patterns:
    - Controller / Router
    - Adapter (HTTP -> UseCase)
    - Error Mapping
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from app.application.usecases import (
    ArchiveWorkspaceUseCase,
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
    GetWorkspaceUseCase,
    ListWorkspacesUseCase,
    PublishWorkspaceUseCase,
    ShareWorkspaceUseCase,
    UpdateWorkspaceUseCase,
    WorkspaceError,
    WorkspaceErrorCode,
)
from app.audit import emit_audit_event
from app.container import (
    get_archive_workspace_use_case,
    get_audit_repository,
    get_create_workspace_use_case,
    get_get_workspace_use_case,
    get_list_workspaces_use_case,
    get_publish_workspace_use_case,
    get_share_workspace_use_case,
    get_update_workspace_use_case,
)
from app.crosscutting.error_responses import (
    conflict,
    forbidden,
    internal_error,
    not_found,
    service_unavailable,
    validation_error,
)
from app.domain.entities import Workspace
from app.domain.repositories import AuditEventRepository
from app.domain.workspace_policy import WorkspaceActor
from app.identity.dual_auth import (
    Principal,
    require_admin,
    require_employee_or_admin,
    require_principal,
)
from app.identity.rbac import Permission
from fastapi import APIRouter, Depends, Query

from ..schemas.workspaces import (
    ArchiveWorkspaceRes,
    CreateWorkspaceReq,
    ShareWorkspaceReq,
    UpdateWorkspaceReq,
    WorkspaceACL,
    WorkspaceRes,
    WorkspacesListRes,
)

router = APIRouter()


# =============================================================================
# Helpers internos (puros / sin IO)
# =============================================================================


def _to_workspace_actor(principal: Principal | None) -> WorkspaceActor | None:
    """
    Traduce Principal (HTTP) al actor usado por la policy del dominio.
    """
    if principal and principal.user:
        return WorkspaceActor(
            user_id=principal.user.user_id,
            roles=[principal.user.role.value],
        )
    return None


def _raise_workspace_error(
    error: WorkspaceError, *, workspace_id: UUID | None = None
) -> None:
    """
    Traduce WorkspaceError (application layer) a RFC7807.
    """
    if error.code == WorkspaceErrorCode.VALIDATION_ERROR:
        raise validation_error(error.message)

    if error.code == WorkspaceErrorCode.NOT_FOUND:
        raise not_found("Workspace", str(workspace_id or "-"))

    if error.code == WorkspaceErrorCode.FORBIDDEN:
        raise forbidden("No tenés permisos para acceder a este workspace")

    if error.code == WorkspaceErrorCode.CONFLICT:
        raise conflict(error.message)

    # Fallback defensivo (no debería ocurrir)
    raise internal_error(error.message)


def _to_workspace_res(ws: Workspace) -> WorkspaceRes:
    """
    Mapea entidad de dominio -> DTO HTTP.
    """
    return WorkspaceRes(
        id=ws.id,
        name=ws.name,
        visibility=ws.visibility,
        owner_user_id=ws.owner_user_id,
        description=ws.description,
        acl=WorkspaceACL(allowed_roles=list(ws.allowed_roles or [])),
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        archived_at=ws.archived_at,
    )


def _require_active_workspace(
    workspace_id: UUID,
    use_case: GetWorkspaceUseCase,
    actor: WorkspaceActor | None,
) -> None:
    """
    Enforce: workspace existe y no está archivado.
    """
    result = use_case.execute(workspace_id, actor=actor)

    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    if result.workspace is None:
        raise service_unavailable("Workspace")

    if result.workspace.is_archived:
        raise validation_error("El workspace está archivado")


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/workspaces",
    response_model=WorkspacesListRes,
    tags=["workspaces"],
)
def list_workspaces(
    owner_user_id: UUID | None = Query(None),
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    use_case: ListWorkspacesUseCase = Depends(get_list_workspaces_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)

    result = use_case.execute(
        actor=actor,
        owner_user_id=owner_user_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    if result.error is not None:
        _raise_workspace_error(result.error)

    workspaces = result.workspaces or []
    next_offset = offset + limit if len(workspaces) == limit else None

    return WorkspacesListRes(
        workspaces=[_to_workspace_res(ws) for ws in workspaces],
        next_offset=next_offset,
    )


@router.post(
    "/workspaces",
    response_model=WorkspaceRes,
    status_code=201,
    tags=["workspaces"],
)
def create_workspace(
    req: CreateWorkspaceReq,
    use_case: CreateWorkspaceUseCase = Depends(get_create_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)

    input_data = CreateWorkspaceInput(
        name=req.name,
        visibility=req.visibility,
        owner_user_id=principal.user.user_id if principal and principal.user else None,
        description=req.description,
        allowed_roles=req.allowed_roles,
        actor=actor,
    )

    result = use_case.execute(input_data)
    if result.error is not None:
        _raise_workspace_error(result.error)

    if result.workspace is None:
        raise service_unavailable("Workspace")

    emit_audit_event(
        audit_repo,
        action="workspace.create",
        principal=principal,
        target_id=result.workspace.id,
        workspace_id=result.workspace.id,
        metadata={"visibility": str(result.workspace.visibility)},
    )
    return _to_workspace_res(result.workspace)


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def get_workspace(
    workspace_id: UUID,
    use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)

    result = use_case.execute(workspace_id, actor=actor)
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    if result.workspace is None:
        raise service_unavailable("Workspace")

    return _to_workspace_res(result.workspace)


@router.patch(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def update_workspace(
    workspace_id: UUID,
    req: UpdateWorkspaceReq,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: UpdateWorkspaceUseCase = Depends(get_update_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        workspace_id=workspace_id,
        actor=actor,
        name=req.name,
        description=req.description,
        visibility=req.visibility,
        allowed_roles=req.allowed_roles,
    )

    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    if result.workspace is None:
        raise service_unavailable("Workspace")

    emit_audit_event(
        audit_repo,
        action="workspace.update",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )
    return _to_workspace_res(result.workspace)


@router.post(
    "/workspaces/{workspace_id}/publish",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def publish_workspace(
    workspace_id: UUID,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: PublishWorkspaceUseCase = Depends(get_publish_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(workspace_id=workspace_id, actor=actor)
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    if result.workspace is None:
        raise service_unavailable("Workspace")

    emit_audit_event(
        audit_repo,
        action="workspace.publish",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )
    return _to_workspace_res(result.workspace)


@router.post(
    "/workspaces/{workspace_id}/share",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def share_workspace(
    workspace_id: UUID,
    req: ShareWorkspaceReq,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: ShareWorkspaceUseCase = Depends(get_share_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        workspace_id=workspace_id, actor=actor, user_ids=req.user_ids
    )
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    if result.workspace is None:
        raise service_unavailable("Workspace")

    emit_audit_event(
        audit_repo,
        action="workspace.share",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
        metadata={"user_ids": [str(x) for x in req.user_ids]},
    )
    return _to_workspace_res(result.workspace)


@router.post(
    "/workspaces/{workspace_id}/archive",
    response_model=ArchiveWorkspaceRes,
    tags=["workspaces"],
)
def archive_workspace(
    workspace_id: UUID,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: ArchiveWorkspaceUseCase = Depends(get_archive_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(workspace_id=workspace_id, actor=actor)
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspace.archive",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )
    return ArchiveWorkspaceRes(workspace_id=workspace_id, archived=True)


@router.delete(
    "/workspaces/{workspace_id}",
    response_model=ArchiveWorkspaceRes,
    tags=["workspaces"],
)
def delete_workspace(
    workspace_id: UUID,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: ArchiveWorkspaceUseCase = Depends(get_archive_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """
    Delete lógico (alias de archive). No se borra físicamente.
    """
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(workspace_id=workspace_id, actor=actor)
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspace.delete",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )
    return ArchiveWorkspaceRes(workspace_id=workspace_id, archived=True)
