"""
Repository Implementations (Infrastructure Layer).

This module provides concrete implementations of domain repository interfaces.

Structure:
    - postgres/     Production implementations (SQLAlchemy + PostgreSQL)
    - in_memory/    Testing & development implementations (ephemeral)
    - redis/        (Future) Caching and rate limiting

Usage:
    # Production
    from app.infrastructure.repositories.postgres import PostgresDocumentRepository

    # Testing
    from app.infrastructure.repositories.in_memory import InMemoryFeedbackRepository

Factory Pattern:
    Use get_repository() for DI-friendly instantiation.
"""

# =============================================================================
# In-Memory Implementations (Testing/Development)
# =============================================================================
from .in_memory import (
    InMemoryAnswerAuditRepository,
    InMemoryConversationRepository,
    InMemoryFeedbackRepository,
    InMemoryWorkspaceAclRepository,
    InMemoryWorkspaceRepository,
)

# =============================================================================
# PostgreSQL Implementations (Production)
# =============================================================================
from .postgres import (
    PostgresAuditEventRepository,
    PostgresConnectorSourceRepository,
    PostgresDocumentRepository,
    PostgresUserRepository,
    PostgresWorkspaceAclRepository,
    PostgresWorkspaceRepository,
)

# =============================================================================
# Public API
# =============================================================================
__all__ = [
    # Postgres
    "PostgresConnectorSourceRepository",
    "PostgresDocumentRepository",
    "PostgresWorkspaceRepository",
    "PostgresWorkspaceAclRepository",
    "PostgresAuditEventRepository",
    "PostgresUserRepository",
    # In-Memory
    "InMemoryFeedbackRepository",
    "InMemoryAnswerAuditRepository",
    "InMemoryConversationRepository",
    "InMemoryWorkspaceRepository",
    "InMemoryWorkspaceAclRepository",
]
