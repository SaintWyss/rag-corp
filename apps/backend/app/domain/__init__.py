"""
===============================================================================
TARJETA CRC — domain/__init__.py
===============================================================================

Módulo:
    Exportaciones de la Capa de Dominio (API pública del dominio)

Responsabilidades:
    - Centralizar exports para imports limpios en application/interfaces.
    - Mantener estable el “surface area” del dominio.
    - Evitar imports profundos y acoplamientos innecesarios.

Colaboradores:
    - domain.entities: Entidades (Document, Chunk, QueryResult, ...)
    - domain.repositories: Puertos de persistencia
    - domain.services: Puertos de servicios externos
    - domain.value_objects: Objetos de valor (citas, filtros, cuotas, etc.)

Reglas:
    - Solo re-exporta contratos/entidades del dominio.
    - No importar infraestructura aquí.
===============================================================================
"""

from .entities import Chunk, ConversationMessage, Document, QueryResult
from .repositories import (
    AnswerAuditRepository,
    AuditEventRepository,
    ConversationRepository,
    DocumentRepository,
    FeedbackRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from .services import EmbeddingService, LLMService, TextChunkerService
from .value_objects import (
    AnswerAuditRecord,
    ConfidenceScore,
    FeedbackVote,
    MetadataFilter,
    SourceReference,
    UsageQuota,
    calculate_confidence,
)

__all__ = [
    # Entities
    "Document",
    "Chunk",
    "QueryResult",
    "ConversationMessage",
    # Repository Interfaces (Ports)
    "DocumentRepository",
    "WorkspaceRepository",
    "WorkspaceAclRepository",
    "ConversationRepository",
    "AuditEventRepository",
    "FeedbackRepository",
    "AnswerAuditRepository",
    # Service Interfaces (Ports)
    "EmbeddingService",
    "LLMService",
    "TextChunkerService",
    # Value Objects
    "SourceReference",
    "ConfidenceScore",
    "calculate_confidence",
    "MetadataFilter",
    "UsageQuota",
    "FeedbackVote",
    "AnswerAuditRecord",
]
