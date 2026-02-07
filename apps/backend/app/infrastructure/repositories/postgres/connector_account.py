"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres/connector_account.py
============================================================
Class: PostgresConnectorAccountRepository

Responsibilities:
  - Implementar persistencia de ConnectorAccount en PostgreSQL.
  - Upsert por (workspace_id, provider) — idempotente.
  - Tokens almacenados cifrados (responsabilidad de la capa de aplicación).

Collaborators:
  - domain.connectors (ConnectorAccount, ConnectorProvider)
  - infrastructure.db.pool (get_pool)
  - psycopg_pool.ConnectionPool
============================================================
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....domain.connectors import ConnectorAccount, ConnectorProvider

_TABLE = "connector_accounts"

_SELECT_COLUMNS = """
    id, workspace_id, provider, account_email,
    encrypted_refresh_token, created_at, updated_at
"""


class PostgresConnectorAccountRepository:
    """Implementación PostgreSQL del repositorio de ConnectorAccount."""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        if self._pool is not None:
            return self._pool
        from app.infrastructure.db.pool import get_pool

        return get_pool()

    @staticmethod
    def _row_to_entity(row: tuple) -> ConnectorAccount:
        (
            account_id,
            workspace_id,
            provider,
            account_email,
            encrypted_refresh_token,
            created_at,
            updated_at,
        ) = row
        return ConnectorAccount(
            id=account_id,
            workspace_id=workspace_id,
            provider=ConnectorProvider(provider),
            account_email=account_email,
            encrypted_refresh_token=encrypted_refresh_token,
            created_at=created_at,
            updated_at=updated_at,
        )

    def upsert(self, account: ConnectorAccount) -> None:
        """Crea o actualiza cuenta (idempotente por workspace+provider)."""
        sql = f"""
            INSERT INTO {_TABLE}
                (id, workspace_id, provider, account_email, encrypted_refresh_token,
                 created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (workspace_id, provider) DO UPDATE SET
                account_email = EXCLUDED.account_email,
                encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                updated_at = now()
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(
                    sql,
                    (
                        account.id,
                        account.workspace_id,
                        account.provider.value,
                        account.account_email,
                        account.encrypted_refresh_token,
                        account.created_at,
                        account.updated_at,
                    ),
                )
        except Exception as exc:
            logger.exception(
                "connector_account.upsert failed",
                extra={"workspace_id": str(account.workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_account.upsert: {exc}") from exc

    def get_by_workspace(
        self, workspace_id: UUID, provider: ConnectorProvider
    ) -> Optional[ConnectorAccount]:
        sql = (
            f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} "
            f"WHERE workspace_id = %s AND provider = %s"
        )
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(sql, (workspace_id, provider.value)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        except Exception as exc:
            logger.exception(
                "connector_account.get_by_workspace failed",
                extra={"workspace_id": str(workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_account.get_by_workspace: {exc}") from exc

    def delete(self, account_id: UUID) -> bool:
        sql = f"DELETE FROM {_TABLE} WHERE id = %s"
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(sql, (account_id,))
                return (result.rowcount or 0) > 0
        except Exception as exc:
            logger.exception(
                "connector_account.delete failed",
                extra={"account_id": str(account_id), "error": str(exc)},
            )
            raise DatabaseError(f"connector_account.delete: {exc}") from exc
