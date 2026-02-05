"""
===============================================================================
CRC CARD — infrastructure/db/instrumentation.py
===============================================================================

Clases:
  - TimedConnection (Proxy)
  - InstrumentedConnectionPool (Facade/Proxy)

Responsabilidades:
  - Medir duración de conn.execute(...) sin tocar repositorios.
  - Loguear slow queries (baja cardinalidad).
  - Healthcheck opcional al adquirir conexión (SELECT 1).

Colaboradores:
  - crosscutting.logger
  - psycopg_pool.ConnectionPool (pool real)
===============================================================================
"""

from __future__ import annotations

import os
import time
from typing import Any, ContextManager

from ...crosscutting.logger import logger
from ...crosscutting.metrics import observe_db_query_duration
from .errors import DatabaseConnectionError


def _statement_kind(sql: Any) -> str:
    """
    Extrae un “tipo” de statement para logs (baja cardinalidad).
    """
    try:
        s = str(sql).lstrip().split(None, 1)[0].upper()
        return s if s else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


class TimedConnection:
    """
    Proxy de conexión: intercepta execute para medir tiempo.

    Importante:
      - Delegamos TODO al conn real con __getattr__ (Facade/Proxy).
      - Solo “envolvemos” execute().
    """

    def __init__(self, inner_conn, *, slow_query_seconds: float) -> None:
        self._conn = inner_conn
        self._slow = slow_query_seconds

    def execute(self, sql, *args, **kwargs):
        start = time.perf_counter()
        try:
            return self._conn.execute(sql, *args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            kind = _statement_kind(sql)
            observe_db_query_duration(kind, elapsed)
            if elapsed >= self._slow:
                logger.warning(
                    "DB query lenta",
                    extra={"kind": kind, "seconds": round(elapsed, 4)},
                )

    def __getattr__(self, item: str):
        return getattr(self._conn, item)


class _ConnectionContext(ContextManager[TimedConnection]):
    """
    Context manager que envuelve el context manager del pool.
    """

    def __init__(
        self, inner_ctx, *, slow_query_seconds: float, healthcheck: bool
    ) -> None:
        self._inner_ctx = inner_ctx
        self._slow = slow_query_seconds
        self._healthcheck = healthcheck
        self._conn = None

    def __enter__(self) -> TimedConnection:
        try:
            conn = self._inner_ctx.__enter__()
            if self._healthcheck:
                # Asegura estado limpio (evita transacciones abortadas del uso previo).
                # psycopg permite rollback seguro aunque no haya transacción activa.
                try:
                    conn.rollback()
                except Exception:
                    pass
                # Limpia prepared statements para evitar colisiones en pool.
                try:
                    conn.execute("DEALLOCATE ALL")
                except Exception:
                    pass
                # Healthcheck rápido (evita conexiones zombis).
                conn.execute("SELECT 1")
            self._conn = TimedConnection(conn, slow_query_seconds=self._slow)
            return self._conn
        except Exception as exc:
            raise DatabaseConnectionError(
                "No se pudo adquirir/validar conexión DB."
            ) from exc

    def __exit__(self, exc_type, exc, tb) -> bool:
        return self._inner_ctx.__exit__(exc_type, exc, tb)


class InstrumentedConnectionPool:
    """
    Facade del pool real.

    Objetivo:
      - Que repositorios sigan haciendo: `with pool.connection() as conn:`
      - Pero `conn` sea un TimedConnection (instrumentado).
    """

    def __init__(self, inner_pool) -> None:
        self._pool = inner_pool
        self._slow_seconds = float(os.getenv("DB_SLOW_QUERY_SECONDS", "0.25"))
        self._healthcheck = os.getenv("DB_HEALTHCHECK_ON_ACQUIRE", "true").lower() in {
            "1",
            "true",
            "yes",
        }

    def connection(self, *args, **kwargs) -> ContextManager[TimedConnection]:
        inner_ctx = self._pool.connection(*args, **kwargs)
        return _ConnectionContext(
            inner_ctx,
            slow_query_seconds=self._slow_seconds,
            healthcheck=self._healthcheck,
        )

    # Delegación del resto del API del pool.
    def __getattr__(self, item: str):
        return getattr(self._pool, item)
