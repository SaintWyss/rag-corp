"""
Name: Admin Routes (Workspace Provisioning)

Responsibilities:
  - Allow ADMIN to create workspaces for specific users
  - Allow ADMIN to list workspaces by owner_user_id
  - ADR-008: Admin-only provisioning endpoints

Collaborators:
  - CreateWorkspaceUseCase (reused with admin override)
  - ListWorkspacesUseCase
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..application.usecases.create_workspace import (
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
)
from ..application.usecases.list_workspaces import ListWorkspacesUseCase
from ..audit import emit_audit_event
from ..container import (
    get_audit_repository,
    get_create_workspace_use_case,
    get_list_workspaces_use_case,
)
from ..crosscutting.error_responses import OPENAPI_ERROR_RESPONSES, forbidden
from ..domain.entities import WorkspaceVisibility
from ..domain.repositories import AuditEventRepository
from ..domain.workspace_policy import WorkspaceActor
from ..identity.dual_auth import Principal, require_admin, require_principal
from ..identity.rbac import Permission

router = APIRouter(prefix="/admin", tags=["admin"], responses=OPENAPI_ERROR_RESPONSES)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class AdminCreateWorkspaceReq(BaseModel):
    """Request to create a workspace for a specific user."""

    owner_user_id: UUID = Field(..., description="User ID who will own the workspace")
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: str | None = Field(
        None, max_length=1024, description="Workspace description"
    )


class WorkspaceRes(BaseModel):
    """Workspace response for admin endpoints."""

    id: UUID
    name: str
    description: str | None
    visibility: WorkspaceVisibility
    owner_user_id: UUID | None
    created_at: str | None
    updated_at: str | None
    archived_at: str | None


class WorkspacesListRes(BaseModel):
    """List of workspaces response."""

    workspaces: list[WorkspaceRes]


# =============================================================================
# HELPERS
# =============================================================================


def _to_workspace_res(workspace) -> WorkspaceRes:
    """Convert domain workspace to response model."""
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
    """Convert Principal to WorkspaceActor for use case calls."""
    if not principal or not principal.user:
        return None
    return WorkspaceActor(
        user_id=principal.user.user_id,
        role=principal.user.role,
    )


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post(
    "/workspaces",
    response_model=WorkspaceRes,
    status_code=201,
    summary="Create workspace for user (admin-only)",
    description="ADR-008: Admin can create a workspace and assign it to a specific user.",
)
def admin_create_workspace(
    req: AdminCreateWorkspaceReq,
    use_case: CreateWorkspaceUseCase = Depends(get_create_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """
    Create a workspace for a specific user.

    - Only admin can use this endpoint.
    - The workspace is created with owner_user_id set to the specified user.
    - Visibility defaults to PRIVATE.
    """
    actor = _to_workspace_actor(principal)
    if not actor:
        raise forbidden("Admin authentication required.")

    result = use_case.execute(
        CreateWorkspaceInput(
            name=req.name,
            description=req.description,
            actor=actor,
            visibility=WorkspaceVisibility.PRIVATE,
            owner_user_id=req.owner_user_id,  # R: Admin assigns owner
        )
    )

    if result.error:
        from ..crosscutting.error_responses import bad_request, conflict

        if result.error.code.value == "conflict":
            raise conflict(result.error.message)
        raise bad_request(result.error.message)

    workspace = result.workspace

    emit_audit_event(
        audit_repo,
        action="admin.workspaces.create",
        principal=principal,
        target_id=workspace.id,
        workspace_id=workspace.id,
        metadata={
            "assigned_owner": str(req.owner_user_id),
            "name": req.name,
        },
    )

    return _to_workspace_res(workspace)


@router.get(
    "/users/{user_id}/workspaces",
    response_model=WorkspacesListRes,
    summary="List workspaces for user (admin-only)",
    description="ADR-008: Admin can view all workspaces owned by a specific user.",
)
def admin_list_user_workspaces(
    user_id: UUID,
    include_archived: bool = False,
    use_case: ListWorkspacesUseCase = Depends(get_list_workspaces_use_case),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    """
    List all workspaces owned by a specific user.

    - Only admin can use this endpoint.
    - Returns workspaces where owner_user_id matches the specified user_id.
    """
    actor = _to_workspace_actor(principal)
    if not actor:
        raise forbidden("Admin authentication required.")

    result = use_case.execute(
        actor=actor,
        owner_user_id=user_id,  # R: Filter by specific owner
        include_archived=include_archived,
    )

    if result.error:
        raise forbidden(result.error.message)

    return WorkspacesListRes(
        workspaces=[_to_workspace_res(ws) for ws in result.workspaces]
    )
