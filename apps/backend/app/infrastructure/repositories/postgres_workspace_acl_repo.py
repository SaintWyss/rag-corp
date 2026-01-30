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

from ...crosscutting.exceptions import DatabaseError
from ...crosscutting.logger import logger


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

    def __init__(self, pool: Optional[ConnectionPool] = None):
        # Pool inyectable para tests. En prod se obtiene por factory global.
        self._pool = pool

    # ... (omitir methods intermedios que no cambian) ...

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

        except Exception as exc:
            logger.exception(
                "PostgresWorkspaceAclRepository: Failed to replace workspace ACL",
                extra={"error": str(exc), "workspace_id": str(workspace_id)},
            )
            raise DatabaseError(f"Failed to replace workspace ACL: {exc}") from exc
