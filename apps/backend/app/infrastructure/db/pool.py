"""
===============================================================================
CRC CARD — infrastructure/db/pool.py
===============================================================================

Componente:
  Pool de conexiones PostgreSQL (singleton)

Responsabilidades:
  - Inicializar, exponer y cerrar el pool de conexiones.
  - Configurar conexiones: pgvector + statement_timeout.
  - Devolver un pool instrumentado (observabilidad sin tocar repos).

Colaboradores:
  - psycopg_pool.ConnectionPool
  - pgvector.psycopg.register_vector
  - infrastructure/db/instrumentation.InstrumentedConnectionPool

Principios:
  - Fail-fast (config incorrecta, doble init, uso sin init)
  - Encapsulación (pool global único)
===============================================================================
"""

from __future__ import annotations

import threading
from typing import Optional

from pgvector.psycopg import register_vector

from ...crosscutting.logger import logger
from .errors import PoolAlreadyInitializedError, PoolNotInitializedError
from .instrumentation import InstrumentedConnectionPool

_pool: Optional[InstrumentedConnectionPool] = None
_pool_lock = threading.Lock()


def _configure_connection(conn) -> None:
    """
    Configura una conexión del pool.

    Se ejecuta cuando el pool crea/adquiere conexiones (según implementación del pool).
    """
    # Registrar tipo vectorial (pgvector)
    register_vector(conn)

    # Aplicar statement_timeout (guardrail contra queries colgadas)
    from ...crosscutting.config import get_settings

    timeout_ms = int(get_settings().db_statement_timeout_ms)
    if timeout_ms > 0:
        conn.execute(f"SET statement_timeout = {timeout_ms}")
        conn.commit()


def init_pool(database_url: str, min_size: int, max_size: int):
    """
    Inicializa el pool (una vez por proceso).

    Devuelve un pool instrumentado para mejorar observabilidad.
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            raise PoolAlreadyInitializedError("El pool ya fue inicializado.")

        # Lazy import: el server puede importar módulos sin DB en ciertos escenarios.
        from psycopg_pool import ConnectionPool

        logger.info(
            "Inicializando pool DB",
            extra={"min_size": min_size, "max_size": max_size},
        )

        real_pool = ConnectionPool(
            conninfo=database_url,
            min_size=min_size,
            max_size=max_size,
            configure=_configure_connection,
            open=True,
        )

        _pool = InstrumentedConnectionPool(real_pool)

        logger.info(
            "Pool DB inicializado",
            extra={"min_size": min_size, "max_size": max_size},
        )

        return _pool


def get_pool():
    """
    Retorna el pool instrumentado singleton.
    """
    if _pool is None:
        raise PoolNotInitializedError(
            "Pool no inicializado. Llamar init_pool() primero."
        )
    return _pool


def close_pool() -> None:
    """
    Cierra el pool (idempotente).
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            logger.info("Cerrando pool DB")
            try:
                _pool.close()
            finally:
                _pool = None
            logger.info("Pool DB cerrado")


def reset_pool() -> None:
    """
    Reset para tests.

    Nota:
      - Mantengo esta función porque tu repo la usa en testing.
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
        _pool = None
