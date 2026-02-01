"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/admin.py
===============================================================================

Name:
    Admin Router

Responsibilities:
    - Endpoints administrativos del backend.
    - Hoy: Auditoría (consulta de eventos).
    - Validaciones de borde (rangos de fechas, presencia de repositorio).
    - Enforce de permisos ADMIN_CONFIG y rol admin.

Collaborators:
    - domain.repositories.AuditEventRepository
    - container.get_audit_repository
    - identity.dual_auth.require_admin
    - identity.rbac.Permission
    - schemas.admin

===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.container import get_audit_repository
from app.crosscutting.error_responses import service_unavailable, validation_error
from app.domain.repositories import AuditEventRepository
from app.identity.dual_auth import Principal, require_admin, require_principal
from app.identity.rbac import Permission
from fastapi import APIRouter, Depends, Query

from ..schemas.admin import AuditEventRes, AuditEventsRes

router = APIRouter()


def _to_audit_event_res(event) -> AuditEventRes:
    """
    Adapter defensivo: AuditEvent (dominio) -> DTO HTTP.
    """
    return AuditEventRes(
        id=event.id,
        actor=event.actor,
        action=event.action,
        target_id=event.target_id,
        metadata=event.metadata or {},
        created_at=getattr(event, "created_at", None),
    )


@router.get(
    "/admin/audit",
    response_model=AuditEventsRes,
    tags=["admin"],
)
def list_audit_events(
    workspace_id: UUID | None = Query(None),
    actor_id: str | None = Query(None),
    action_prefix: str | None = Query(None),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    if audit_repo is None:
        raise service_unavailable("Audit repository")

    if start_at and end_at and start_at > end_at:
        raise validation_error("start_at debe ser anterior a end_at")

    events = audit_repo.list_events(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action_prefix=action_prefix,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
        offset=offset,
    )

    next_offset = offset + limit if len(events) == limit else None
    return AuditEventsRes(
        events=[_to_audit_event_res(e) for e in events],
        next_offset=next_offset,
    )
