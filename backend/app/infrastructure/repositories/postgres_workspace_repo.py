"""
Name: PostgreSQL Workspace Repository Implementation

Responsibilities:
  - Implement WorkspaceRepository interface for PostgreSQL
  - Persist workspace metadata with archive semantics
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ...domain.entities import Workspace, WorkspaceVisibility
from ...exceptions import DatabaseError
from ...logger import logger


class PostgresWorkspaceRepository:
    """R: PostgreSQL implementation of WorkspaceRepository."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    def _row_to_workspace(self, row: tuple) -> Workspace:
        (
            workspace_id,
            name,
            description,
            visibility,
            owner_user_id,
            archived_at,
            created_at,
            updated_at,
        ) = row

        return Workspace(
            id=workspace_id,
            name=name,
            description=description,
            visibility=WorkspaceVisibility(visibility),
            owner_user_id=owner_user_id,
            created_at=created_at,
            updated_at=updated_at,
            archived_at=archived_at,
            allowed_roles=[],
            shared_user_ids=[],
        )

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[Workspace]:
        conditions: list[str] = []
        params: list[object] = []

        if owner_user_id is not None:
            conditions.append("owner_user_id = %s")
            params.append(owner_user_id)

        if not include_archived:
            conditions.append("archived_at IS NULL")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, name, description, visibility, owner_user_id,
                   archived_at, created_at, updated_at
            FROM workspaces
            {where_clause}
            ORDER BY created_at DESC NULLS LAST, name ASC
        """

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(query, params).fetchall()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to list workspaces",
                extra={"error": str(exc), "owner_user_id": owner_user_id},
            )
            raise DatabaseError(f"Failed to list workspaces: {exc}")

        return [self._row_to_workspace(row) for row in rows]

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(
                    """
                    SELECT id, name, description, visibility, owner_user_id,
                           archived_at, created_at, updated_at
                    FROM workspaces
                    WHERE id = %s
                    """,
                    (workspace_id,),
                ).fetchone()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to get workspace",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to get workspace: {exc}")

        if not row:
            return None
        return self._row_to_workspace(row)

    def get_workspace_by_owner_and_name(
        self, owner_user_id: UUID | None, name: str
    ) -> Workspace | None:
        if owner_user_id is None:
            return None

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(
                    """
                    SELECT id, name, description, visibility, owner_user_id,
                           archived_at, created_at, updated_at
                    FROM workspaces
                    WHERE owner_user_id = %s AND LOWER(name) = LOWER(%s)
                    """,
                    (owner_user_id, name),
                ).fetchone()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to lookup workspace by owner+name",
                extra={
                    "error": str(exc),
                    "owner_user_id": str(owner_user_id),
                    "name": name,
                },
            )
            raise DatabaseError(f"Failed to lookup workspace: {exc}")

        if not row:
            return None
        return self._row_to_workspace(row)

    def create_workspace(self, workspace: Workspace) -> Workspace:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(
                    """
                    INSERT INTO workspaces (
                        id,
                        name,
                        description,
                        visibility,
                        owner_user_id,
                        archived_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, description, visibility, owner_user_id,
                              archived_at, created_at, updated_at
                    """,
                    (
                        workspace.id,
                        workspace.name,
                        workspace.description,
                        workspace.visibility.value,
                        workspace.owner_user_id,
                        workspace.archived_at,
                    ),
                ).fetchone()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to create workspace",
                extra={"error": str(exc), "workspace_id": str(workspace.id)},
            )
            raise DatabaseError(f"Failed to create workspace: {exc}")

        if not row:
            raise DatabaseError("Failed to create workspace: no row returned")
        return self._row_to_workspace(row)

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: WorkspaceVisibility | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Workspace | None:
        fields: list[str] = []
        params: list[object] = []

        if name is not None:
            fields.append("name = %s")
            params.append(name)

        if description is not None:
            fields.append("description = %s")
            params.append(description)

        if visibility is not None:
            fields.append("visibility = %s")
            params.append(visibility.value)

        # R: Workspace table doesn't persist allowed_roles (ACL stored separately).
        _ = allowed_roles

        if not fields:
            return self.get_workspace(workspace_id)

        fields.append("updated_at = NOW()")

        query = f"""
            UPDATE workspaces
            SET {", ".join(fields)}
            WHERE id = %s
            RETURNING id, name, description, visibility, owner_user_id,
                      archived_at, created_at, updated_at
        """
        params.append(workspace_id)

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(query, params).fetchone()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to update workspace",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to update workspace: {exc}")

        if not row:
            return None
        return self._row_to_workspace(row)

    def archive_workspace(self, workspace_id: UUID) -> bool:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE workspaces
                    SET archived_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND archived_at IS NULL
                    """,
                    (workspace_id,),
                )
                if cursor.rowcount and cursor.rowcount > 0:
                    return True

                row = conn.execute(
                    "SELECT archived_at FROM workspaces WHERE id = %s",
                    (workspace_id,),
                ).fetchone()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to archive workspace",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to archive workspace: {exc}")

        return row is not None
