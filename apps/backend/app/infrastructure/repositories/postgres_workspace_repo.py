"""
CRC — infrastructure/repositories/postgres_workspace_repo.py

Name
- PostgresWorkspaceRepository

Responsibilities
- Implement WorkspaceRepository for PostgreSQL.
- Provide workspace CRUD and archive semantics (archived_at).
- Provide v6 listing helpers used by application use cases:
  - list_workspaces_by_visibility (e.g., ORG_READ)
  - list_workspaces_by_ids (e.g., SHARED via ACL reverse lookup)

Collaborators
- domain.entities.Workspace, WorkspaceVisibility
- crosscutting.exceptions.DatabaseError
- crosscutting.logger.logger
- psycopg_pool.ConnectionPool

Constraints / Notes
- No business policy here (RBAC/ACL decisions live in domain/application).
- Queries must be parameterized (no string interpolation of user input).
- Methods must respect include_archived flag consistently.
- Ordering should be deterministic and consistent across listing methods.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ...crosscutting.exceptions import DatabaseError
from ...crosscutting.logger import logger
from ...domain.entities import Workspace, WorkspaceVisibility


class PostgresWorkspaceRepository:
    """R: PostgreSQL implementation of WorkspaceRepository."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        # R: Pool is injectable for tests; production uses the global pool factory.
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        # R: Lazy-load the pool when not injected.
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    def _row_to_workspace(self, row: tuple) -> Workspace:
        # R: Keep mapping logic centralized and consistent.
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
            # R: allowed_roles & shared_user_ids are not stored in workspaces table
            # (ACL is stored in workspace_acl). Keep empty here.
            allowed_roles=[],
            shared_user_ids=[],
        )

    def _select_workspaces(
        self,
        *,
        where_sql: str,
        params: list[object],
    ) -> list[Workspace]:
        """
        R: Internal helper to execute a workspace SELECT with deterministic ordering.

        Args:
            where_sql: Must include leading 'WHERE ...' or be empty string.
            params: Parameters for the query (psycopg style).
        """
        query = f"""
            SELECT id, name, description, visibility, owner_user_id,
                   archived_at, created_at, updated_at
            FROM workspaces
            {where_sql}
            ORDER BY created_at DESC NULLS LAST, name ASC
        """

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(query, params).fetchall()
        except Exception as exc:
            logger.warning(
                "PostgresWorkspaceRepository: Failed to select workspaces",
                extra={"error": str(exc), "where_sql": where_sql},
            )
            raise DatabaseError(f"Failed to select workspaces: {exc}")

        return [self._row_to_workspace(row) for row in rows]

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """
        R: List workspaces (optionally filtered by owner).
        """
        conditions: list[str] = []
        params: list[object] = []

        if owner_user_id is not None:
            conditions.append("owner_user_id = %s")
            params.append(owner_user_id)

        if not include_archived:
            conditions.append("archived_at IS NULL")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self._select_workspaces(where_sql=where_sql, params=params)

    def list_workspaces_by_visibility(
        self,
        visibility: WorkspaceVisibility,
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """
        R: List workspaces filtered by visibility (e.g., ORG_READ).

        Notes:
            - Used by v6 employee listing logic to fetch org-visible workspaces.
            - This method does not apply any user policy; it only filters by visibility.
        """
        conditions: list[str] = ["visibility = %s"]
        params: list[object] = [visibility.value]

        if not include_archived:
            conditions.append("archived_at IS NULL")

        where_sql = f"WHERE {' AND '.join(conditions)}"
        return self._select_workspaces(where_sql=where_sql, params=params)

    def list_workspaces_by_ids(
        self,
        workspace_ids: list[UUID],
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """
        R: List workspaces by an explicit set of IDs.

        Contract requirements:
            - Return [] when workspace_ids is empty.
            - Do not raise if some IDs don't exist; just skip them.
            - Respect include_archived.
        """
        if not workspace_ids:
            # R: Avoid generating invalid SQL and avoid unnecessary DB round-trip.
            return []

        # R: Use placeholders to remain fully parameterized.
        placeholders = ", ".join(["%s"] * len(workspace_ids))
        conditions: list[str] = [f"id IN ({placeholders})"]
        params: list[object] = list(workspace_ids)

        if not include_archived:
            conditions.append("archived_at IS NULL")

        where_sql = f"WHERE {' AND '.join(conditions)}"
        return self._select_workspaces(where_sql=where_sql, params=params)

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """
        R: Fetch a workspace by ID.
        """
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
        self,
        owner_user_id: UUID | None,
        name: str,
    ) -> Workspace | None:
        """
        R: Fetch a workspace by owner + name (used for uniqueness checks).
        """
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
        """
        R: Persist a new workspace.
        """
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
        """
        R: Update workspace attributes.

        Note:
            - allowed_roles are not stored in workspaces table (ACL is separate).
        """
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

        # R: Explicitly ignore allowed_roles here (ACL stored separately).
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
        """
        R: Archive (soft-delete) a workspace (sets archived_at).
        """
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
