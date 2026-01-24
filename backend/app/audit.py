"""
Name: Audit Logging Helpers

Responsibilities:
  - Normalize actor/metadata for audit events
  - Best-effort persistence (never break request flow)
"""

from __future__ import annotations

from uuid import UUID, uuid4

from .domain.audit import AuditEvent
from .domain.repositories import AuditEventRepository
from .identity.dual_auth import Principal, PrincipalType
from .crosscutting.logger import logger


def _actor_from_principal(principal: Principal | None) -> str:
    if not principal:
        return "anonymous"
    if principal.principal_type == PrincipalType.USER and principal.user:
        return f"user:{principal.user.user_id}"
    if principal.principal_type == PrincipalType.SERVICE and principal.service:
        return f"service:{principal.service.api_key_hash}"
    return "unknown"


def _metadata_from_principal(principal: Principal | None) -> dict[str, str]:
    if not principal:
        return {"principal_type": "anonymous"}
    if principal.principal_type == PrincipalType.USER and principal.user:
        return {
            "principal_type": "user",
            "email": principal.user.email,
            "role": principal.user.role.value,
        }
    if principal.principal_type == PrincipalType.SERVICE and principal.service:
        return {
            "principal_type": "service",
            "rbac_role": principal.service.rbac_role or "",
        }
    return {"principal_type": "unknown"}


def emit_audit_event(
    repository: AuditEventRepository | None,
    *,
    action: str,
    principal: Principal | None = None,
    actor: str | None = None,
    target_id: UUID | None = None,
    workspace_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    if repository is None:
        return

    payload = {
        **_metadata_from_principal(principal),
        **(metadata or {}),
    }
    if workspace_id is not None:
        payload["workspace_id"] = str(workspace_id)

    event = AuditEvent(
        id=uuid4(),
        actor=actor or _actor_from_principal(principal),
        action=action,
        target_id=target_id,
        metadata=payload,
    )

    try:
        repository.record_event(event)
    except Exception as exc:
        logger.warning(
            "Audit event write failed",
            extra={"action": action, "error": str(exc)},
        )
