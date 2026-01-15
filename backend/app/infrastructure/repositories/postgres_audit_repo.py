"""
Name: PostgreSQL Audit Repository

Responsibilities:
  - Persist audit events to PostgreSQL
"""

from typing import Optional

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ...domain.audit import AuditEvent
from ...exceptions import DatabaseError
from ...logger import logger


class PostgresAuditEventRepository:
    """R: PostgreSQL implementation of AuditEventRepository."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    def record_event(self, event: AuditEvent) -> None:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_events (id, actor, action, target_id, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        event.id,
                        event.actor,
                        event.action,
                        event.target_id,
                        Json(event.metadata),
                    ),
                )
        except Exception as exc:
            logger.warning(
                "PostgresAuditEventRepository: Failed to record audit event",
                extra={"error": str(exc), "action": event.action},
            )
            raise DatabaseError(f"Failed to record audit event: {exc}")
