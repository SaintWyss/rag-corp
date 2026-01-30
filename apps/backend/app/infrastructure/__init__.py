# infrastructure/repositories/__init__.py
"""
============================================================
TARJETA CRC — infrastructure/repositories/__init__.py
============================================================
Module: infrastructure.repositories (Public Export Surface)

Responsibilities:
  - Exponer una API pública y estable de repositorios de infraestructura.
  - Centralizar imports/exports para evitar paths largos en el resto del código.
  - Mantener un orden lógico (Postgres primero, luego InMemory).
  - Evitar “import spaghetti” y facilitar refactors futuros.

Collaborators:
  - Repositorios concretos (Postgres*, InMemory*)
  - Capas superiores (application/use-cases) que importan desde este módulo

Policy:
  - Este archivo NO contiene lógica de negocio.
  - Solo re-exporta símbolos; no debe tener side effects.
============================================================
"""

# ------------------------------------------------------------
# In-memory implementations (tests / local dev)
# ------------------------------------------------------------
from .in_memory_conversation_repo import InMemoryConversationRepository
from .in_memory_workspace_acl_repo import InMemoryWorkspaceAclRepository
from .in_memory_workspace_repo import InMemoryWorkspaceRepository

# ------------------------------------------------------------
# PostgreSQL implementations (infra real)
# ------------------------------------------------------------
from .postgres_audit_repo import PostgresAuditEventRepository
from .postgres_document_repo import PostgresDocumentRepository
from .postgres_user_repo import PostgresUserRepository
from .postgres_workspace_acl_repo import PostgresWorkspaceAclRepository
from .postgres_workspace_repo import PostgresWorkspaceRepository

# ------------------------------------------------------------
# Public API of this package
# ------------------------------------------------------------
__all__ = [
    # Postgres
    "PostgresAuditEventRepository",
    "PostgresDocumentRepository",
    "PostgresUserRepository",
    "PostgresWorkspaceRepository",
    "PostgresWorkspaceAclRepository",
    # InMemory
    "InMemoryConversationRepository",
    "InMemoryWorkspaceRepository",
    "InMemoryWorkspaceAclRepository",
]
