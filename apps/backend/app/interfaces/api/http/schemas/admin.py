"""
===============================================================================
TARJETA CRC — schemas/admin.py
===============================================================================

Módulo:
    Schemas HTTP para Admin / Auditoría

Responsabilidades:
    - DTOs de response para endpoints administrativos (audit, health extendido).
    - Mantener contratos estables para observabilidad.

Colaboradores:
    - domain.audit.AuditEvent
===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEventRes(BaseModel):
    """Evento de auditoría serializable."""

    id: UUID
    actor: str
    action: str
    target_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class AuditEventsRes(BaseModel):
    """Listado paginado simple (offset-based)."""

    events: list[AuditEventRes]
    next_offset: int | None = None
