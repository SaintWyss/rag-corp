"""Infra DB: pool + errores tipados + utilidades."""

from .errors import (
    DatabaseConnectionError,
    DatabasePoolError,
    PoolAlreadyInitializedError,
    PoolNotInitializedError,
)
from .pool import close_pool, get_pool, init_pool

__all__ = [
    "init_pool",
    "get_pool",
    "close_pool",
    "DatabasePoolError",
    "PoolAlreadyInitializedError",
    "PoolNotInitializedError",
    "DatabaseConnectionError",
]
