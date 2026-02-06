"""
===============================================================================
CHAT USE CASES PACKAGE (Public API / Exports)
===============================================================================

Name:
    Chat Use Cases (package exports)

Business Goal:
    Exponer una API pública, estable y explícita para los casos de uso de Chat
    (RAG), centralizando imports de:
      - Core RAG:
          * AnswerQueryUseCase (Q&A sincrónico con RAG)
          * SearchChunksUseCase (búsqueda semántica)
      - Conversation Management:
          * CreateConversationUseCase (iniciar sesión de chat)
          * GetConversationHistoryUseCase (recuperar historial)
          * AnswerQueryWithHistoryUseCase (RAG + persistencia)
          * ClearConversationUseCase (limpiar historial)
      - Feedback & Audit:
          * VoteAnswerUseCase (RLHF - feedback del usuario)
          * RecordAnswerAuditUseCase (compliance empresarial)

Why (Context / Intención):
    - Facilita descubrimiento de capacidades del subdominio Chat.
    - Evita imports dispersos en capas superiores (API/UI).
    - Define un "contrato público" del paquete mediante __all__.
    - Separa claramente:
        * Operaciones RAG puras (stateless)
        * Operaciones de conversación (stateful / con historial)
        * Operaciones de feedback y auditoría (mejora continua)
===============================================================================
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Core RAG Use Cases (Stateless)
# -----------------------------------------------------------------------------
from .answer_query import AnswerQueryInput, AnswerQueryUseCase
from .answer_query_with_history import (
    AnswerQueryWithHistoryInput,
    AnswerQueryWithHistoryUseCase,
)

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
from .chat_utils import format_conversation_for_prompt, truncate_history
from .clear_conversation import (
    ClearConversationInput,
    ClearConversationResult,
    ClearConversationUseCase,
)

# -----------------------------------------------------------------------------
# Conversation Management Use Cases (Stateful)
# -----------------------------------------------------------------------------
from .create_conversation import (
    CreateConversationInput,
    CreateConversationResult,
    CreateConversationUseCase,
)
from .get_conversation_history import (
    GetConversationHistoryInput,
    GetConversationHistoryResult,
    GetConversationHistoryUseCase,
)
from .record_answer_audit import (
    RecordAnswerAuditInput,
    RecordAnswerAuditResult,
    RecordAnswerAuditUseCase,
)
from .search_chunks import SearchChunksInput, SearchChunksUseCase

# -----------------------------------------------------------------------------
# Feedback & Audit Use Cases (RLHF / Compliance)
# -----------------------------------------------------------------------------
from .vote_answer import VoteAnswerInput, VoteAnswerResult, VoteAnswerUseCase

# -----------------------------------------------------------------------------
# Public API (explicit exports)
# -----------------------------------------------------------------------------
__all__ = [
    # Core RAG (stateless)
    "AnswerQueryInput",
    "AnswerQueryUseCase",
    "SearchChunksInput",
    "SearchChunksUseCase",
    # Conversation: Create
    "CreateConversationInput",
    "CreateConversationResult",
    "CreateConversationUseCase",
    # Conversation: History
    "GetConversationHistoryInput",
    "GetConversationHistoryResult",
    "GetConversationHistoryUseCase",
    # Conversation: Answer with persistence
    "AnswerQueryWithHistoryInput",
    "AnswerQueryWithHistoryUseCase",
    # Conversation: Clear
    "ClearConversationInput",
    "ClearConversationResult",
    "ClearConversationUseCase",
    # Feedback (RLHF)
    "VoteAnswerInput",
    "VoteAnswerResult",
    "VoteAnswerUseCase",
    # Audit (Compliance)
    "RecordAnswerAuditInput",
    "RecordAnswerAuditResult",
    "RecordAnswerAuditUseCase",
    # Utilities
    "format_conversation_for_prompt",
    "truncate_history",
]
