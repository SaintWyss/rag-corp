"""
===============================================================================
TARJETA CRC — domain/audit.py
===============================================================================

Módulo:
    Modelos de Auditoría (Dominio)

Responsabilidades:
    - Definir estructuras de datos para auditoría (AuditEvent).
    - Mantener el contrato de auditoría independiente de infraestructura.

Colaboradores:
    - domain.repositories.AuditEventRepository: persiste y lista eventos.
    - app/audit.py: emite eventos (orquestación).
    - infra repos: mapean hacia/desde DB.

Notas:
    - Auditoría suele ser append-only (no se edita ni se borra).
    - metadata es flexible (dict).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AuditEvent:
    """Evento de auditoría del sistema."""

    id: UUID
    actor: str
    action: str
    target_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
