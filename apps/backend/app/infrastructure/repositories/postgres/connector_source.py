"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres/connector_source.py
============================================================
Class: PostgresConnectorSourceRepository

Responsibilities:
  - Implementar persistencia de ConnectorSource en PostgreSQL.
  - CRUD completo + update_status / update_cursor.
  - Scoped por workspace_id (multi-tenant boundary).

Collaborators:
  - domain.connectors (ConnectorSource, ConnectorProvider, ConnectorSourceStatus)
  - infrastructure.db.pool (get_pool)
  - psycopg_pool.ConnectionPool
============================================================
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....domain.connectors import (
    ConnectorProvider,
    ConnectorSource,
    ConnectorSourceStatus,
)

_TABLE = "connector_sources"

_SELECT_COLUMNS = """
    id, workspace_id, provider, folder_id, status,
    cursor_json, created_at, updated_at
"""


class PostgresConnectorSourceRepository:
    """Implementación PostgreSQL del repositorio de ConnectorSource."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool
        from app.infrastructure.db.pool import get_pool

        return get_pool()

    # -----------------------------------------------------------------
    # Mapping
    # -----------------------------------------------------------------
    @staticmethod
    def _row_to_entity(row: tuple) -> ConnectorSource:
        (
            source_id,
            workspace_id,
            provider,
            folder_id,
            status,
            cursor_json,
            created_at,
            updated_at,
        ) = row
        return ConnectorSource(
            id=source_id,
            workspace_id=workspace_id,
            provider=ConnectorProvider(provider),
            folder_id=folder_id,
            status=ConnectorSourceStatus(status),
            cursor_json=cursor_json or {},
            created_at=created_at,
            updated_at=updated_at,
        )

    # -----------------------------------------------------------------
    # CRUD
    # -----------------------------------------------------------------
    def create(self, source: ConnectorSource) -> None:
        sql = f"""
            INSERT INTO {_TABLE}
                (id, workspace_id, provider, folder_id, status, cursor_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(
                    sql,
                    (
                        source.id,
                        source.workspace_id,
                        source.provider.value,
                        source.folder_id,
                        source.status.value,
                        Json(source.cursor_json or {}),
                        source.created_at,
                        source.updated_at,
                    ),
                )
        except Exception as exc:
            logger.exception(
                "connector_source.create failed",
                extra={"source_id": str(source.id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.create: {exc}") from exc

    def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        provider: ConnectorProvider | None = None,
    ) -> List[ConnectorSource]:
        conditions = ["workspace_id = %s"]
        params: list[object] = [workspace_id]

        if provider is not None:
            conditions.append("provider = %s")
            params.append(provider.value)

        where = " AND ".join(conditions)
        sql = f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} WHERE {where} ORDER BY created_at DESC"

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(sql, tuple(params)).fetchall()
            return [self._row_to_entity(r) for r in rows]
        except Exception as exc:
            logger.exception(
                "connector_source.list_by_workspace failed",
                extra={"workspace_id": str(workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.list_by_workspace: {exc}") from exc

    def get(self, source_id: UUID) -> Optional[ConnectorSource]:
        sql = f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} WHERE id = %s"
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(sql, (source_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        except Exception as exc:
            logger.exception(
                "connector_source.get failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.get: {exc}") from exc

    def update_status(self, source_id: UUID, status: ConnectorSourceStatus) -> None:
        sql = f"UPDATE {_TABLE} SET status = %s, updated_at = now() WHERE id = %s"
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(sql, (status.value, source_id))
        except Exception as exc:
            logger.exception(
                "connector_source.update_status failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.update_status: {exc}") from exc

    def update_cursor(self, source_id: UUID, cursor_json: Dict[str, Any]) -> None:
        sql = f"UPDATE {_TABLE} SET cursor_json = %s, updated_at = now() WHERE id = %s"
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(sql, (Json(cursor_json), source_id))
        except Exception as exc:
            logger.exception(
                "connector_source.update_cursor failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.update_cursor: {exc}") from exc

    def delete(self, source_id: UUID) -> bool:
        sql = f"DELETE FROM {_TABLE} WHERE id = %s"
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(sql, (source_id,))
                return (result.rowcount or 0) > 0
        except Exception as exc:
            logger.exception(
                "connector_source.delete failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.delete: {exc}") from exc

    def try_set_syncing(self, source_id: UUID) -> bool:
        """
        Intenta marcar el source como SYNCING (CAS atómico).

        Retorna True si se pudo adquirir el lock (status cambió a SYNCING).
        Retorna False si ya estaba SYNCING (otro sync en curso).
        """
        sql = f"""
            UPDATE {_TABLE}
            SET status = %s, updated_at = now()
            WHERE id = %s AND status != %s
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    sql,
                    (
                        ConnectorSourceStatus.SYNCING.value,
                        source_id,
                        ConnectorSourceStatus.SYNCING.value,
                    ),
                )
                return (result.rowcount or 0) > 0
        except Exception as exc:
            logger.exception(
                "connector_source.try_set_syncing failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_source.try_set_syncing: {exc}") from exc
