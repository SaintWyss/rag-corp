"""
Name: PostgreSQL Connection Pool

Responsibilities:
  - Manage connection pool lifecycle (init, get, close)
  - Configure connections with pgvector and statement_timeout
  - Provide singleton pool instance

Collaborators:
  - psycopg_pool: Connection pooling
  - pgvector: Vector type registration
  - config: Pool settings

Constraints:
  - Singleton pattern (one pool per process)
  - Must init before use, close on shutdown
  - register_vector must be called per connection

Notes:
  - Uses psycopg_pool.ConnectionPool
  - Configure callback sets up each connection
  - Thread-safe
"""

from typing import Optional
import threading

from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from ...logger import logger


# R: Singleton pool instance
_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def _configure_connection(conn) -> None:
    """
    R: Configure a connection from the pool.

    Called for each connection when acquired from pool.
    Registers pgvector type and sets statement_timeout.
    """
    # R: Register vector type for this connection
    register_vector(conn)

    # R: Set statement timeout if configured
    from ...config import get_settings

    timeout_ms = get_settings().db_statement_timeout_ms
    if timeout_ms > 0:
        conn.execute(f"SET statement_timeout = {timeout_ms}")
        conn.commit()


def init_pool(database_url: str, min_size: int, max_size: int) -> ConnectionPool:
    """
    R: Initialize the connection pool.

    Args:
        database_url: PostgreSQL connection string
        min_size: Minimum connections to maintain
        max_size: Maximum connections allowed

    Returns:
        Initialized ConnectionPool

    Raises:
        RuntimeError: If pool already initialized
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            raise RuntimeError("Connection pool already initialized")

        logger.info(
            "Initializing connection pool",
            extra={"min_size": min_size, "max_size": max_size},
        )

        _pool = ConnectionPool(
            conninfo=database_url,
            min_size=min_size,
            max_size=max_size,
            configure=_configure_connection,
            open=True,
        )

        logger.info(
            "Connection pool initialized",
            extra={"min_size": min_size, "max_size": max_size},
        )

        return _pool


def get_pool() -> ConnectionPool:
    """
    R: Get the connection pool singleton.

    Returns:
        ConnectionPool instance

    Raises:
        RuntimeError: If pool not initialized
    """
    if _pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _pool


def close_pool() -> None:
    """
    R: Close the connection pool.

    Safe to call even if pool not initialized.
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            logger.info("Closing connection pool")
            _pool.close()
            _pool = None
            logger.info("Connection pool closed")


def reset_pool() -> None:
    """
    R: Reset pool for testing.

    Closes existing pool if any, allowing re-initialization.
    """
    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()
        _pool = None
