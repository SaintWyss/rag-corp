"""
============================================================
TARJETA CRC
============================================================
Class: app.infrastructure.repositories (Package exports)

Responsibilities:
- Exponer implementaciones concretas de repositorios (Postgres e InMemory)
  en un único punto de importación.
- Mantener una API estable para la capa de aplicación (use cases).

Collaborators:
- Repositorios Postgres (SQL crudo)
- Repositorios InMemory (testing / fallback)
============================================================
"""

# ---------------------------
# In-memory implementations
# Usados para tests unitarios rápidos o entornos volátiles.
# No persisten datos tras reiniciar la app.
# ---------------------------
from .in_memory_conversation_repo import InMemoryConversationRepository
from .in_memory_workspace_acl_repo import InMemoryWorkspaceAclRepository
from .in_memory_workspace_repo import InMemoryWorkspaceRepository

# ---------------------------
# Postgres implementations
# Implementaciones de producción con persistencia real y transacciones.
# PostgresDocumentRepository incluye lógica de vectores (pgvector).
# ---------------------------
from .postgres_audit_repo import PostgresAuditEventRepository
from .postgres_document_repo import PostgresDocumentRepository
from .postgres_workspace_acl_repo import PostgresWorkspaceAclRepository
from .postgres_workspace_repo import PostgresWorkspaceRepository

__all__ = [
    # Postgres
    "PostgresWorkspaceRepository",
    "PostgresWorkspaceAclRepository",
    "PostgresDocumentRepository",
    "PostgresAuditEventRepository",
    # In-memory
    "InMemoryWorkspaceRepository",
    "InMemoryWorkspaceAclRepository",
    "InMemoryConversationRepository",
]
