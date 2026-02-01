"""
===============================================================================
CRC CARD — infrastructure/db/errors.py
===============================================================================

Componente:
  Errores tipados del Pool/Conectividad

Responsabilidades:
  - Evitar RuntimeError genéricos.
  - Dar semántica clara: "no inicializado", "ya inicializado", etc.
===============================================================================
"""


class DatabasePoolError(Exception):
    """Base de errores de pool de base de datos."""


class PoolAlreadyInitializedError(DatabasePoolError):
    """Se intentó inicializar el pool más de una vez."""


class PoolNotInitializedError(DatabasePoolError):
    """Se intentó usar el pool sin init_pool()."""


class DatabaseConnectionError(DatabasePoolError):
    """Error al adquirir o validar una conexión del pool."""
