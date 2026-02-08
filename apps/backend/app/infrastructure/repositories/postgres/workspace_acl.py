"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres_workspace_acl_repo.py
============================================================
Class: PostgresWorkspaceAclRepository

Responsibilities:
- Implementar acceso a datos de ACL de Workspaces en PostgreSQL (SQL crudo).
- Gestionar la “lista de compartidos” para workspaces con visibilidad SHARED (tabla workspace_acl).
- Proveer lookup directo (users de un workspace) y lookup inverso (workspaces de un user).
- Reemplazar ACL completa de un workspace de forma transaccional (delete + insert).

Collaborators:
- psycopg_pool.ConnectionPool
- crosscutting.exceptions.DatabaseError
- crosscutting.logger.logger
- Tabla: workspace_acl(workspace_id, user_id, access, created_at)

Constraints / Notes (Clean / KISS):
- Repo puro: NO aplica reglas de negocio/RBAC (eso vive en domain/application).
- Todas las queries deben ser parametrizadas.
- Ordenamiento determinístico para respuestas/tests estables.
- Operaciones de “replace” deben ser transaccionales (todo o nada).
============================================================
"""

from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....domain.entities import AclEntry, AclRole


class PostgresWorkspaceAclRepository:
    """
    Repositorio PostgreSQL para ACL de workspaces.

    Modelo mental:
    - workspace_acl representa “quién puede acceder a un workspace compartido”.
    - Cada fila es un permiso: (workspace_id, user_id, access).
    - Se espera unicidad por par (workspace_id, user_id) vía PK/unique constraint.
    """

    # =========================================================
    # SQL Constantes (Privadas)
    # Patrón: extraer SQL para evitar ruido visual en la lógica
    # =========================================================
    _SQL_LIST_WORKSPACE_ACL = """
        SELECT user_id
        FROM workspace_acl
        WHERE workspace_id = %s
        ORDER BY created_at ASC, user_id ASC
    """

    _SQL_LIST_WORKSPACES_FOR_USER = """
        SELECT workspace_id
        FROM workspace_acl
        WHERE user_id = %s
        ORDER BY created_at ASC, workspace_id ASC
    """

    _SQL_DELETE_ACL = "DELETE FROM workspace_acl WHERE workspace_id = %s"

    _SQL_INSERT_BATCH = """
        INSERT INTO workspace_acl (workspace_id, user_id, access)
        SELECT %s, u.user_id, 'READ'
        FROM UNNEST(%s::uuid[]) AS u(user_id)
        ON CONFLICT (workspace_id, user_id)
        DO UPDATE SET access = EXCLUDED.access
    """

    # --- ACL management (con rol) ---
    _SQL_GRANT_ACCESS = """
        INSERT INTO workspace_acl (workspace_id, user_id, role, granted_by, access)
        VALUES (%s, %s, %s, %s, 'READ')
        ON CONFLICT (workspace_id, user_id)
        DO UPDATE SET role = EXCLUDED.role, granted_by = EXCLUDED.granted_by
        RETURNING workspace_id, user_id, role, granted_by, created_at
    """

    _SQL_REVOKE_ACCESS = """
        DELETE FROM workspace_acl
        WHERE workspace_id = %s AND user_id = %s
    """

    _SQL_LIST_ACL_ENTRIES = """
        SELECT workspace_id, user_id, role, granted_by, created_at
        FROM workspace_acl
        WHERE workspace_id = %s
        ORDER BY created_at ASC, user_id ASC
    """

    def __init__(self, pool: Optional[ConnectionPool] = None):
        # Pool inyectable para tests. En prod se obtiene por factory global.
        self._pool = pool

    # =========================================================
    # Helpers (DRY + errores consistentes)
    # =========================================================
    def _get_pool(self) -> ConnectionPool:
        """Pool lazy-load."""
        if self._pool is not None:
            return self._pool
        from app.infrastructure.db.pool import get_pool

        return get_pool()

    def _fetchall(
        self, *, query: str, params: Iterable[object], context_msg: str, extra: dict
    ) -> list[tuple]:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchall()
        except Exception as exc:
            logger.exception(context_msg, extra={**extra, "error": str(exc)})
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    def _fetchone(
        self, *, query: str, params: Iterable[object], context_msg: str, extra: dict
    ) -> tuple | None:
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchone()
        except Exception as exc:
            logger.exception(context_msg, extra={**extra, "error": str(exc)})
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    # =========================================================
    # Public API
    # =========================================================
    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        """
        Devuelve la lista de user_ids que tienen acceso al workspace.

        Orden determinístico:
        - created_at ASC (primero los más antiguos)
        - user_id ASC (desempate estable)
        """
        rows = self._fetchall(
            query=self._SQL_LIST_WORKSPACE_ACL,
            params=[workspace_id],
            context_msg="PostgresWorkspaceAclRepository: Failed to list workspace ACL",
            extra={"workspace_id": str(workspace_id)},
        )

        # rows = [(uuid,), (uuid,), ...] -> devolvemos [uuid, uuid, ...]
        return [row[0] for row in rows]

    def list_workspaces_for_user(self, user_id: UUID) -> list[UUID]:
        """
        Lookup inverso:
        Devuelve los workspace_ids donde el usuario aparece en la ACL.

        Orden determinístico:
        - created_at ASC
        - workspace_id ASC
        """
        rows = self._fetchall(
            query=self._SQL_LIST_WORKSPACES_FOR_USER,
            params=[user_id],
            context_msg="PostgresWorkspaceAclRepository: Failed to list workspaces for user",
            extra={"user_id": str(user_id)},
        )

        # Defensive uniqueness (redundante pero robusto)
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
        Reemplaza completamente la ACL de un workspace.
        """
        # Deduplicación estable
        unique_ids: list[UUID] = list(dict.fromkeys(user_ids))

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                # Transacción explícita
                with conn.transaction():
                    # 1) Borrado total selectivo en vez de hardcode
                    conn.execute(self._SQL_DELETE_ACL, (workspace_id,))

                    # 2) Si no hay usuarios, terminamos (ACL vacía)
                    if not unique_ids:
                        return

                    # 3) Inserción batch optimizada
                    conn.execute(
                        self._SQL_INSERT_BATCH,
                        (workspace_id, unique_ids),
                    )

        except Exception as exc:
            logger.exception(
                "PostgresWorkspaceAclRepository: Failed to replace workspace ACL",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to replace workspace ACL: {exc}") from exc

    # =========================================================
    # ACL Management (grant / revoke / list_entries)
    # =========================================================
    def grant_access(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: AclRole = AclRole.VIEWER,
        *,
        granted_by: UUID | None = None,
    ) -> AclEntry:
        """Otorga acceso (upsert). Retorna la entrada creada/actualizada."""
        row = self._fetchone(
            query=self._SQL_GRANT_ACCESS,
            params=[workspace_id, user_id, role.value, granted_by],
            context_msg="PostgresWorkspaceAclRepository: Failed to grant access",
            extra={"workspace_id": str(workspace_id), "user_id": str(user_id)},
        )
        if row is None:  # pragma: no cover — RETURNING siempre devuelve
            raise DatabaseError("Unexpected: RETURNING clause returned no rows")
        return AclEntry(
            workspace_id=row[0],
            user_id=row[1],
            role=AclRole(row[2]),
            granted_by=row[3],
            created_at=row[4],
        )

    def revoke_access(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Revoca acceso. Retorna True si existía la entrada."""
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(self._SQL_REVOKE_ACCESS, (workspace_id, user_id))
                return (result.rowcount or 0) > 0
        except Exception as exc:
            logger.exception(
                "PostgresWorkspaceAclRepository: Failed to revoke access",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to revoke access: {exc}") from exc

    def list_acl_entries(self, workspace_id: UUID) -> list[AclEntry]:
        """Lista entradas ACL con rol y metadata."""
        rows = self._fetchall(
            query=self._SQL_LIST_ACL_ENTRIES,
            params=[workspace_id],
            context_msg="PostgresWorkspaceAclRepository: Failed to list ACL entries",
            extra={"workspace_id": str(workspace_id)},
        )
        return [
            AclEntry(
                workspace_id=row[0],
                user_id=row[1],
                role=AclRole(row[2]),
                granted_by=row[3],
                created_at=row[4],
            )
            for row in rows
        ]
