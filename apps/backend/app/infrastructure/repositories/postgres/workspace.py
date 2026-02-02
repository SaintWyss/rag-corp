"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres_workspace_repo.py
============================================================
Class: PostgresWorkspaceRepository

Responsibilities:
- Implementar acceso a datos de Workspaces en PostgreSQL (SQL crudo).
- Proveer operaciones CRUD + semántica de archivado (soft-delete via archived_at).
- Exponer listados determinísticos y reutilizables por la capa de aplicación:
  - list_workspaces()
  - list_workspaces_by_visibility()
  - list_workspaces_by_ids()
  - list_workspaces_visible_to_user()
  - get_workspace(), get_workspace_by_owner_and_name()
  - create_workspace(), update_workspace(), archive_workspace()

Collaborators:
- domain.entities.Workspace, WorkspaceVisibility
- crosscutting.exceptions.DatabaseError
- crosscutting.logger.logger
- psycopg_pool.ConnectionPool
- Tablas: workspaces, workspace_acl

Constraints / Notes (Clean / KISS):
- Sin lógica de negocio aquí (RBAC/ACL/políticas viven arriba). Este repo solo “filtra” y “devuelve”.
- Queries siempre parametrizadas (nada de interpolación de input de usuario).
- include_archived debe respetarse de forma consistente en listados.
- Ordenamiento determinístico en todos los listados.
============================================================
"""

from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....domain.entities import Workspace, WorkspaceVisibility


class PostgresWorkspaceRepository:
    """R: Implementación PostgreSQL del repositorio de Workspaces."""

    # R: SELECT base reutilizable (mismo orden de columnas para mapping consistente)
    _SELECT_COLUMNS = """
        id, name, description, visibility, owner_user_id,
        archived_at, created_at, updated_at
    """

    # R: Orden determinístico: primero más recientes, luego nombre (estable)
    _ORDER_BY = "ORDER BY created_at DESC NULLS LAST, name ASC"

    def __init__(self, pool: Optional[ConnectionPool] = None):
        # R: Pool inyectable para tests; en producción se obtiene por factory global.
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        # R: Lazy-load para no acoplarse fuerte en import-time.
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    # =========================================================
    # Mapping
    # =========================================================
    def _row_to_workspace(self, row: tuple) -> Workspace:
        # R: Mapping centralizado para mantener consistencia.
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
            # R: allowed_roles & shared_user_ids NO viven en workspaces (ACL está en workspace_acl).
            allowed_roles=[],
            shared_user_ids=[],
        )

    # =========================================================
    # Helpers de ejecución (DRY + errores consistentes)
    # =========================================================
    def _fetchall(
        self, *, query: str, params: Iterable[object], context_msg: str, extra: dict
    ) -> list[tuple]:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchall()
        except Exception as exc:
            logger.exception(
                context_msg,
                extra={**extra, "error": str(exc)},
            )
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    def _fetchone(
        self, *, query: str, params: Iterable[object], context_msg: str, extra: dict
    ) -> tuple | None:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchone()
        except Exception as exc:
            logger.exception(
                context_msg,
                extra={**extra, "error": str(exc)},
            )
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    # =========================================================
    # Internal query builders
    # =========================================================
    def _select_workspaces(
        self,
        *,
        where_sql: str,
        params: list[object],
    ) -> list[Workspace]:
        """
        R: Helper interno para SELECT con orden determinístico.

        where_sql:
          - Debe ser "" o comenzar con "WHERE ..."
          - Se construye SOLO desde este repositorio (no desde input del usuario).
        """
        query = f"""
            SELECT {self._SELECT_COLUMNS}
            FROM workspaces
            {where_sql}
            {self._ORDER_BY}
        """

        rows = self._fetchall(
            query=query,
            params=params,
            context_msg="PostgresWorkspaceRepository: Failed to select workspaces",
            extra={"where_sql": where_sql},
        )
        return [self._row_to_workspace(r) for r in rows]

    # =========================================================
    # Public API
    # =========================================================
    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """R: Lista workspaces (opcionalmente filtrado por owner)."""
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
        R: Lista workspaces por visibilidad (ej: ORG_READ).
        Nota: este método NO aplica política de usuario; solo filtra por visibilidad.
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
        R: Lista workspaces por un conjunto explícito de IDs.

        Contrato:
        - Si workspace_ids está vacío => []
        - Si algunos IDs no existen => se omiten (no error)
        - Respeta include_archived
        """
        if not workspace_ids:
            return []

        # R: Versión PRO (más limpia que IN con placeholders dinámicos):
        #     id = ANY(%s::uuid[])
        # Esto evita construir SQL con N placeholders y reduce complejidad accidental.
        conditions: list[str] = ["id = ANY(%s::uuid[])"]
        params: list[object] = [workspace_ids]

        if not include_archived:
            conditions.append("archived_at IS NULL")

        where_sql = f"WHERE {' AND '.join(conditions)}"
        return self._select_workspaces(where_sql=where_sql, params=params)

    def list_workspaces_visible_to_user(
        self,
        user_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """
        R: Lista workspaces visibles para un usuario en una sola query.
        Semántica (datos, no política):
        - owner_user_id = user
        - OR visibility = ORG_READ
        - OR visibility = SHARED y existe ACL para el usuario
        """
        conditions: list[str] = [
            "("
            "owner_user_id = %s "
            "OR visibility = %s "
            "OR (visibility = %s AND EXISTS ("
            "  SELECT 1 FROM workspace_acl wa "
            "  WHERE wa.workspace_id = workspaces.id AND wa.user_id = %s"
            ")))"
        ]
        params: list[object] = [
            user_id,
            WorkspaceVisibility.ORG_READ.value,
            WorkspaceVisibility.SHARED.value,
            user_id,
        ]

        if not include_archived:
            conditions.append("archived_at IS NULL")

        where_sql = f"WHERE {' AND '.join(conditions)}"
        return self._select_workspaces(where_sql=where_sql, params=params)

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """R: Obtiene un workspace por ID."""
        row = self._fetchone(
            query=f"""
                SELECT {self._SELECT_COLUMNS}
                FROM workspaces
                WHERE id = %s
            """,
            params=[workspace_id],
            context_msg="PostgresWorkspaceRepository: Failed to get workspace",
            extra={"workspace_id": str(workspace_id)},
        )

        return None if not row else self._row_to_workspace(row)

    def get_workspace_by_owner_and_name(
        self,
        owner_user_id: UUID | None,
        name: str,
    ) -> Workspace | None:
        """
        R: Busca workspace por owner + name (usado para checks de unicidad lógica).
        Nota: usa LOWER(name) para comparación case-insensitive.
        """
        if owner_user_id is None:
            return None

        row = self._fetchone(
            query=f"""
                SELECT {self._SELECT_COLUMNS}
                FROM workspaces
                WHERE owner_user_id = %s AND LOWER(name) = LOWER(%s)
            """,
            params=[owner_user_id, name],
            context_msg="PostgresWorkspaceRepository: Failed to lookup workspace by owner+name",
            extra={"owner_user_id": str(owner_user_id), "name": name},
        )

        return None if not row else self._row_to_workspace(row)

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """R: Persiste un workspace nuevo."""
        row = self._fetchone(
            query="""
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
            params=[
                workspace.id,
                workspace.name,
                workspace.description,
                workspace.visibility.value,
                workspace.owner_user_id,
                workspace.archived_at,
            ],
            context_msg="PostgresWorkspaceRepository: Failed to create workspace",
            extra={"workspace_id": str(workspace.id)},
        )

        if not row:
            raise DatabaseError(
                "PostgresWorkspaceRepository: Failed to create workspace: no row returned"
            )
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
        R: Actualiza atributos del workspace.

        Nota:
        - allowed_roles NO se persiste en workspaces (ACL es tabla separada).
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

        # R: Se ignora explícitamente (documentación de contrato)
        _ = allowed_roles

        if not fields:
            return self.get_workspace(workspace_id)

        # R: Mantener updated_at consistente desde DB.
        fields.append("updated_at = NOW()")

        query = f"""
            UPDATE workspaces
            SET {", ".join(fields)}
            WHERE id = %s
            RETURNING id, name, description, visibility, owner_user_id,
                      archived_at, created_at, updated_at
        """
        params.append(workspace_id)

        row = self._fetchone(
            query=query,
            params=params,
            context_msg="PostgresWorkspaceRepository: Failed to update workspace",
            extra={"workspace_id": str(workspace_id)},
        )

        return None if not row else self._row_to_workspace(row)

    def archive_workspace(self, workspace_id: UUID) -> bool:
        """
        R: Archiva (soft-delete) un workspace (set archived_at).

        Contract (explícito):
        - True  => el workspace existe (se haya archivado en esta llamada o ya estuviera archivado)
        - False => el workspace no existe
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

                # R: Idempotencia: si ya estaba archivado, no hacemos update, pero igual existe.
                if cursor.rowcount and cursor.rowcount > 0:
                    return True

                row = conn.execute(
                    "SELECT archived_at FROM workspaces WHERE id = %s",
                    (workspace_id,),
                ).fetchone()
        except Exception as exc:
            logger.exception(
                "PostgresWorkspaceRepository: Failed to archive workspace",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to archive workspace: {exc}") from exc

        return row is not None
