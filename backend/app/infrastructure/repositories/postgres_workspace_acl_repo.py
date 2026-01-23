"""
Name: PostgreSQL Workspace ACL Repository

Responsibilities:
  - Implement WorkspaceAclRepository interface for PostgreSQL
  - Manage shared access lists for workspaces
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ...platform.exceptions import DatabaseError
from ...platform.logger import logger


class PostgresWorkspaceAclRepository:
    """R: PostgreSQL implementation of WorkspaceAclRepository."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT user_id
                    FROM workspace_acl
                    WHERE workspace_id = %s
                    ORDER BY created_at ASC
                    """,
                    (workspace_id,),
                ).fetchall()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceAclRepository: Failed to list workspace ACL",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to list workspace ACL: {exc}")

        return [row[0] for row in rows]

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: list[UUID]) -> None:
        unique_ids = list(dict.fromkeys(user_ids))
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(
                    "DELETE FROM workspace_acl WHERE workspace_id = %s",
                    (workspace_id,),
                )
                for user_id in unique_ids:
                    conn.execute(
                        """
                        INSERT INTO workspace_acl (workspace_id, user_id, access)
                        VALUES (%s, %s, 'READ')
                        ON CONFLICT (workspace_id, user_id)
                        DO UPDATE SET access = EXCLUDED.access
                        """,
                        (workspace_id, user_id),
                    )
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceAclRepository: Failed to replace workspace ACL",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to replace workspace ACL: {exc}")
