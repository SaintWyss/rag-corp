"""
Name: PostgreSQL Audit Repository

Responsibilities:
  - Persist audit events to PostgreSQL
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ...domain.audit import AuditEvent
from ...platform.exceptions import DatabaseError
from ...platform.logger import logger


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

    def list_events(
        self,
        *,
        workspace_id: UUID | None = None,
        actor_id: str | None = None,
        action_prefix: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        conditions: list[str] = []
        params: list[object] = []

        if workspace_id:
            conditions.append("metadata->>'workspace_id' = %s")
            params.append(str(workspace_id))

        if actor_id:
            if ":" in actor_id:
                conditions.append("actor = %s")
                params.append(actor_id)
            else:
                conditions.append("actor LIKE %s")
                params.append(f"%:{actor_id}")

        if action_prefix:
            conditions.append("action LIKE %s")
            params.append(f"{action_prefix}%")

        if start_at:
            conditions.append("created_at >= %s")
            params.append(start_at)

        if end_at:
            conditions.append("created_at <= %s")
            params.append(end_at)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, actor, action, target_id, metadata, created_at
            FROM audit_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(query, params).fetchall()
        except Exception as exc:
            logger.warning(
                "PostgresAuditEventRepository: Failed to list audit events",
                extra={"error": str(exc), "action_prefix": action_prefix},
            )
            raise DatabaseError(f"Failed to list audit events: {exc}")

        events: list[AuditEvent] = []
        for row in rows:
            event_id, actor, action, target_id, metadata, created_at = row
            events.append(
                AuditEvent(
                    id=event_id,
                    actor=actor,
                    action=action,
                    target_id=target_id,
                    metadata=metadata or {},
                    created_at=created_at,
                )
            )
        return events
