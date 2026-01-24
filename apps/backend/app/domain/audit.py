"""
Name: Audit Domain Models

Responsibilities:
  - Define audit event data structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class AuditEvent:
    id: UUID
    actor: str
    action: str
    target_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
