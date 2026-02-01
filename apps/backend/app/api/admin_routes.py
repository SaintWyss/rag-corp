"""
===============================================================================
TARJETA CRC — app/api/admin_routes.py (Provisionamiento Admin)
===============================================================================

Responsabilidades:
  - Exponer endpoints administrativos para provisionamiento de workspaces.
  - Reutilizar casos de uso existentes (sin lógica de negocio en la capa HTTP).
  - Aplicar autorización estricta (permiso ADMIN_CONFIG + rol admin).
  - Emitir auditoría best-effort para acciones administrativas.

Patrones aplicados:
  - Thin Controller: orquesta dependencias, no contiene reglas de negocio.
  - Dependency Injection (FastAPI Depends): inyección explícita de use cases.
  - Error Mapping: traduce errores tipados de casos de uso a HTTP (RFC7807).

Colaboradores:
  - application.usecases.workspace.create_workspace.CreateWorkspaceUseCase
  - application.usecases.workspace.list_workspaces.ListWorkspacesUseCase
  - application.usecases.workspace.workspace_results.WorkspaceErrorCode
  - identity.dual_auth: require_principal, require_admin
  - audit.emit_audit_event
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..application.usecases.workspace.create_workspace import (
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
)
from ..application.usecases.workspace.list_workspaces import ListWorkspacesUseCase
from ..application.usecases.workspace.workspace_results import WorkspaceErrorCode
from ..audit import emit_audit_event
from ..container import (
    get_audit_repository,
    get_create_workspace_use_case,
    get_list_workspaces_use_case,
)
from ..crosscutting.error_responses import (
    OPENAPI_ERROR_RESPONSES,
    bad_request,
    conflict,
    forbidden,
    not_found,
)
from ..domain.entities import WorkspaceVisibility
from ..domain.repositories import AuditEventRepository
from ..domain.workspace_policy import WorkspaceActor
from ..identity.dual_auth import Principal, require_admin, require_principal
from ..identity.rbac import Permission

router = APIRouter(prefix="/admin", tags=["admin"], responses=OPENAPI_ERROR_RESPONSES)


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------


class AdminCreateWorkspaceReq(BaseModel):
    """Request: crear workspace asignándolo a un usuario específico."""

    owner_user_id: UUID = Field(..., description="ID del usuario owner del workspace")
    name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre del workspace"
    )
    description: str | None = Field(
        None, max_length=1024, description="Descripción (opcional)"
    )


class WorkspaceRes(BaseModel):
    """Respuesta: workspace (vista admin)."""

    id: UUID
    name: str
    description: str | None
    visibility: WorkspaceVisibility
    owner_user_id: UUID | None
    created_at: str | None
    updated_at: str | None
    archived_at: str | None


class WorkspacesListRes(BaseModel):
    workspaces: list[WorkspaceRes]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _to_workspace_res(workspace) -> WorkspaceRes:
    """Convierte entidad de dominio a DTO."""
    return WorkspaceRes(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        visibility=workspace.visibility,
        owner_user_id=workspace.owner_user_id,
        created_at=workspace.created_at.isoformat() if workspace.created_at else None,
        updated_at=workspace.updated_at.isoformat() if workspace.updated_at else None,
        archived_at=(
            workspace.archived_at.isoformat() if workspace.archived_at else None
        ),
    )


def _to_workspace_actor(principal: Principal | None) -> WorkspaceActor | None:
    """Convierte Principal a WorkspaceActor para políticas de workspace."""
    if not principal or not principal.user:
        return None
    return WorkspaceActor(user_id=principal.user.user_id, role=principal.user.role)


def _raise_for_workspace_error(error) -> None:
    """
    Traduce WorkspaceError (caso de uso) a HTTP.

    Mantiene el contrato RFC7807 usando factories de error_responses.
    """
    if error.code == WorkspaceErrorCode.VALIDATION_ERROR:
        raise bad_request(error.message)
    if error.code == WorkspaceErrorCode.CONFLICT:
        raise conflict(error.message)
    if error.code == WorkspaceErrorCode.NOT_FOUND:
        raise not_found("Workspace", error.message)
    if error.code == WorkspaceErrorCode.FORBIDDEN:
        raise forbidden(error.message)

    # Fallback defensivo.
    raise bad_request(error.message)


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/workspaces",
    response_model=WorkspaceRes,
    status_code=201,
    summary="Crear workspace para usuario (admin)",
)
def admin_create_workspace(
    req: AdminCreateWorkspaceReq,
    use_case: CreateWorkspaceUseCase = Depends(get_create_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """
    Crea un workspace asignando owner_user_id explícito.

    Reglas:
      - Solo admin.
      - Visibilidad inicial: PRIVATE (evita exposición accidental).
    """
    actor = _to_workspace_actor(principal)
    if not actor:
        raise forbidden("Autenticación admin requerida.")

    result = use_case.execute(
        CreateWorkspaceInput(
            name=req.name,
            description=req.description,
            actor=actor,
            visibility=WorkspaceVisibility.PRIVATE,
            owner_user_id=req.owner_user_id,
        )
    )

    if result.error:
        _raise_for_workspace_error(result.error)

    workspace = result.workspace

    emit_audit_event(
        audit_repo,
        action="admin.workspaces.create",
        principal=principal,
        target_id=workspace.id,
        workspace_id=workspace.id,
        metadata={"assigned_owner": str(req.owner_user_id), "name": req.name},
    )

    return _to_workspace_res(workspace)


@router.get(
    "/users/{user_id}/workspaces",
    response_model=WorkspacesListRes,
    summary="Listar workspaces por usuario (admin)",
)
def admin_list_user_workspaces(
    user_id: UUID,
    include_archived: bool = False,
    use_case: ListWorkspacesUseCase = Depends(get_list_workspaces_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    """Lista workspaces cuyo owner_user_id coincide con user_id."""
    actor = _to_workspace_actor(principal)
    if not actor:
        raise forbidden("Autenticación admin requerida.")

    result = use_case.execute(
        actor=actor,
        owner_user_id=user_id,
        include_archived=include_archived,
    )

    if result.error:
        _raise_for_workspace_error(result.error)

    return WorkspacesListRes(
        workspaces=[_to_workspace_res(ws) for ws in result.workspaces]
    )


__all__ = ["router"]
