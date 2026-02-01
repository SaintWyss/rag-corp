"""
===============================================================================
TARJETA CRC — app/audit.py (Emisión de auditoría)
===============================================================================

Responsabilidades:
  - Construir eventos de auditoría con formato consistente (actor/action/target/metadata).
  - Normalizar actor y metadata a partir del Principal (usuario o servicio).
  - Persistir vía AuditEventRepository (puerto del dominio).
  - “Best-effort”: si falla la persistencia, NO rompe el flujo de negocio.

Colaboradores:
  - app.domain.audit.AuditEvent
  - app.domain.repositories.AuditEventRepository
  - app.identity.dual_auth.Principal / PrincipalType
  - app.crosscutting.logger.logger

Patrones aplicados:
  - Adapter (Principal -> Audit metadata)
  - Best-effort logging (no interrumpe el request)

Decisiones de seguridad:
  - Evitamos guardar PII innecesaria (por defecto NO guardamos email).
  - Metadata se sanitiza a valores serializables; lo no serializable se stringifica.
===============================================================================
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from .crosscutting.logger import logger
from .domain.audit import AuditEvent
from .domain.repositories import AuditEventRepository
from .identity.dual_auth import Principal, PrincipalType


def _actor_from_principal(principal: Principal | None) -> str:
    """
    Construye un identificador de actor estable y fácil de consultar.

    Formato:
      - user:{uuid}
      - service:{hash}
      - anonymous
    """
    if principal is None:
        return "anonymous"

    if principal.principal_type == PrincipalType.USER and principal.user:
        return f"user:{principal.user.user_id}"

    if principal.principal_type == PrincipalType.SERVICE and principal.service:
        # api_key_hash ya es un identificador derivado (no es el secret).
        return f"service:{principal.service.api_key_hash}"

    return "unknown"


def _metadata_from_principal(principal: Principal | None) -> dict[str, Any]:
    """
    Metadata mínima y útil para auditoría (sin PII innecesaria).
    """
    if principal is None:
        return {"principal_type": "anonymous"}

    if principal.principal_type == PrincipalType.USER and principal.user:
        return {
            "principal_type": "user",
            "user_id": str(principal.user.user_id),
            "role": principal.user.role.value,
        }

    if principal.principal_type == PrincipalType.SERVICE and principal.service:
        return {
            "principal_type": "service",
            "rbac_role": principal.service.rbac_role or "",
            "api_key_hash": principal.service.api_key_hash,
        }

    return {"principal_type": "unknown"}


def _sanitize(value: Any) -> Any:
    """
    Convierte valores a tipos serializables para JSON.
    - primitives -> OK
    - dict/list -> sanitiza recursivamente
    - otros -> str(value)
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_sanitize(v) for v in value]

    return str(value)


def emit_audit_event(
    repository: AuditEventRepository | None,
    *,
    action: str,
    principal: Principal | None = None,
    actor: str | None = None,
    target_id: UUID | None = None,
    workspace_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Emite un evento de auditoría.

    Regla clave:
      - Si repository es None o falla al escribir, NO se lanza excepción.
    """
    if repository is None:
        return

    base_metadata = _metadata_from_principal(principal)
    extra_metadata = metadata or {}

    payload: dict[str, Any] = {**base_metadata, **extra_metadata}

    if workspace_id is not None:
        payload["workspace_id"] = str(workspace_id)

    # Sanitización defensiva (evita errores por objetos no serializables).
    payload = _sanitize(payload)

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
        # Best-effort: logueamos y seguimos.
        logger.warning(
            "Falló la escritura del evento de auditoría",
            extra={"action": action, "error": str(exc)},
        )
