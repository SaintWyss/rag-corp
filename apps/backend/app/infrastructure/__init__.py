"""
============================================================
TARJETA CRC — infrastructure/__init__.py
============================================================
Module: app.infrastructure (Package Facade)

Responsibilities:
  - Re-exportar símbolos públicos desde subpaquetes:
      - repositories (Postgres + InMemory)
      - db (pool de conexiones)
      - cache, storage, text, etc. si aplica
  - Proveer un único punto de importación limpio para capas superiores.
  - Evitar que la capa de aplicación conozca la estructura interna de infra.

Collaborators:
  - infrastructure.repositories.* (implementaciones de repos)
  - infrastructure.db.pool (conexión PostgreSQL)

Policy:
  - Este archivo NO contiene lógica.
  - Solo re-exporta; no debe tener side effects al importar.
============================================================
"""

# ------------------------------------------------------------
# Re-export from subpackages
# ------------------------------------------------------------
from .repositories import (  # PostgreSQL (Production); In-Memory (Testing/Development)
    InMemoryAnswerAuditRepository,
    InMemoryConversationRepository,
    InMemoryFeedbackRepository,
    InMemoryWorkspaceAclRepository,
    InMemoryWorkspaceRepository,
    PostgresAuditEventRepository,
    PostgresDocumentRepository,
    PostgresUserRepository,
    PostgresWorkspaceAclRepository,
    PostgresWorkspaceRepository,
)

__all__ = [
    # Postgres
    "PostgresAuditEventRepository",
    "PostgresDocumentRepository",
    "PostgresUserRepository",
    "PostgresWorkspaceRepository",
    "PostgresWorkspaceAclRepository",
    # InMemory
    "InMemoryAnswerAuditRepository",
    "InMemoryConversationRepository",
    "InMemoryFeedbackRepository",
    "InMemoryWorkspaceRepository",
    "InMemoryWorkspaceAclRepository",
]
