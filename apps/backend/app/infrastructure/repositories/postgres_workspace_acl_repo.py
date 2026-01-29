"""
CRC — infrastructure/repositories/postgres_workspace_acl_repo.py

Name
- PostgresWorkspaceAclRepository

Responsibilities
- Implement WorkspaceAclRepository for PostgreSQL.
- Manage shared access lists for SHARED workspaces (workspace_acl table).
- Provide reverse lookup (v6): list workspace IDs shared to a given user.

Collaborators
- psycopg_pool.ConnectionPool
- crosscutting.exceptions.DatabaseError
- crosscutting.logger.logger

Constraints / Notes
- Repository only. No RBAC logic here.
- All queries must be parameterized.
- Ordering should be deterministic for stable responses/tests.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ...crosscutting.exceptions import DatabaseError
from ...crosscutting.logger import logger


class PostgresWorkspaceAclRepository:
    """R: PostgreSQL implementation of WorkspaceAclRepository."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        # R: Pool is injectable for tests; production uses global pool factory.
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        """
        R: List user IDs that have READ access to the given workspace.
        """
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

    def list_workspaces_for_user(self, user_id: UUID) -> list[UUID]:
        """
        R: Reverse lookup: list workspace IDs where the given user is present in ACL.

        This is used by v6 employee listing logic to resolve SHARED workspaces.
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT workspace_id
                    FROM workspace_acl
                    WHERE user_id = %s
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                ).fetchall()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceAclRepository: Failed to list workspaces for user",
                extra={"error": str(exc), "user_id": str(user_id)},
            )
            raise DatabaseError(f"Failed to list workspaces for user: {exc}")

        # R: Defensive uniqueness (should already be unique via PK/unique constraint).
        seen: set[UUID] = set()
        result: list[UUID] = []
        for (workspace_id,) in rows:
            if workspace_id in seen:
                continue
            seen.add(workspace_id)
            result.append(workspace_id)
        return result

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: list[UUID]) -> None:
        """
        R: Replace the ACL for a workspace with the provided user IDs.
        """
        unique_ids = list(dict.fromkeys(user_ids))
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(
                    "DELETE FROM workspace_acl WHERE workspace_id = %s",
                    (workspace_id,),
                )
                for uid in unique_ids:
                    conn.execute(
                        """
                        INSERT INTO workspace_acl (workspace_id, user_id, access)
                        VALUES (%s, %s, 'READ')
                        ON CONFLICT (workspace_id, user_id)
                        DO UPDATE SET access = EXCLUDED.access
                        """,
                        (workspace_id, uid),
                    )
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceAclRepository: Failed to replace workspace ACL",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to replace workspace ACL: {exc}")
