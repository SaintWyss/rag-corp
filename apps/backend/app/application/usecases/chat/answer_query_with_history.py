# =============================================================================
# FILE: application/usecases/chat/answer_query_with_history.py
# =============================================================================
"""
===============================================================================
USE CASE: Answer Query With History (RAG + Conversation Context)
===============================================================================

Name:
    Answer Query With History Use Case

Business Goal:
    Responder una pregunta del usuario usando RAG CON contexto conversacional:
      - Historial persistente (el usuario refresca y su chat sigue ahí)
      - Contexto inyectado al LLM (para que entienda referencias previas)
      - Analytics / RLHF (analizar calidad de respuestas)

Why (Context / Intención):
    - El flujo AnswerQueryUseCase es stateless (no sabe de conversaciones).
    - Este use case orquesta:
        1) Validar conversación existe
        2) Recuperar historial reciente
        3) Formatear historial para inyectar al LLM
        4) Persistir mensaje del usuario
        5) Ejecutar AnswerQueryUseCase con contexto enriquecido
        6) Persistir mensaje del asistente

    - Separation of Concerns:
        * AnswerQueryUseCase: lógica pura de RAG (retrieval + generation)
        * Este use case: orquestación de contexto conversacional + persistencia

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    AnswerQueryWithHistoryUseCase

Responsibilities:
    - Validar existencia de la conversación.
    - Recuperar historial reciente para contexto.
    - Formatear historial usando chat_utils.
    - Persistir mensaje del usuario antes de procesar.
    - Delegar a AnswerQueryUseCase con llm_query enriquecido.
    - Persistir mensaje del asistente después de obtener respuesta.
    - Devolver el resultado del RAG (transparente para el llamador).

Collaborators:
    - ConversationRepository:
        conversation_exists(conversation_id) -> bool
        get_messages(conversation_id, limit) -> List[ConversationMessage]
        append_message(conversation_id, message) -> None
    - AnswerQueryUseCase:
        execute(AnswerQueryInput) -> AnswerQueryResult
    - chat_utils:
        format_conversation_for_prompt(history, query) -> str

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    AnswerQueryWithHistoryInput:
      - conversation_id: str
      - query: str
      - workspace_id: UUID
      - actor: WorkspaceActor | None
      - top_k: int
      - use_mmr: bool
      - history_window: int (default 10, para sliding window)

Outputs:
    AnswerQueryResult (mismo que AnswerQueryUseCase):
      - result: QueryResult | None
      - error: DocumentError | None

Error Mapping:
    - NOT_FOUND:
        * conversación no existe
    - (todos los errores de AnswerQueryUseCase se propagan)
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from ....domain.entities import ConversationMessage
from ....domain.repositories import ConversationRepository
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import (
    AnswerQueryResult,
    DocumentError,
    DocumentErrorCode,
)
from .answer_query import AnswerQueryInput, AnswerQueryUseCase
from .chat_utils import format_conversation_for_prompt

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_RESOURCE_CONVERSATION: Final[str] = "Conversation"
_MSG_CONVERSATION_NOT_FOUND: Final[str] = "Conversation not found."

_DEFAULT_TOP_K: Final[int] = 5
_DEFAULT_HISTORY_WINDOW: Final[int] = 10


@dataclass(frozen=True)
class AnswerQueryWithHistoryInput:
    """
    DTO de entrada para AnswerQuery con contexto conversacional.

    Campos:
      - conversation_id: ID de la conversación existente
      - query: pregunta del usuario
      - workspace_id: scope del retrieval
      - actor: actor para policy de acceso
      - top_k: cantidad de chunks a recuperar
      - use_mmr: retrieval diverso (MMR) vs similarity
      - history_window: cuántos mensajes previos incluir en el contexto (default 10)
    """

    conversation_id: str
    query: str
    workspace_id: UUID
    actor: WorkspaceActor | None
    top_k: int = _DEFAULT_TOP_K
    use_mmr: bool = False
    history_window: int = _DEFAULT_HISTORY_WINDOW


class AnswerQueryWithHistoryUseCase:
    """
    Use Case (Application Service / Orchestration):
        Orquesta el flujo de RAG CON contexto conversacional.

    Estrategia:
        1) Validar conversación existe.
        2) Recuperar historial reciente.
        3) Formatear historial para el LLM.
        4) Persistir mensaje del usuario.
        5) Ejecutar AnswerQueryUseCase con llm_query enriquecido.
        6) Persistir mensaje del asistente (si éxito).
        7) Devolver resultado (transparente).

    Nota:
        - El retrieval usa el query original (mejor para búsqueda semántica).
        - El LLM recibe el historial formateado para entender el contexto.
    """

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        answer_query_use_case: AnswerQueryUseCase,
    ) -> None:
        self._conversations = conversation_repository
        self._answer_query = answer_query_use_case

    def execute(self, input_data: AnswerQueryWithHistoryInput) -> AnswerQueryResult:
        """
        Ejecuta el flujo RAG con contexto conversacional.

        Reglas:
          - La conversación debe existir (pre-condición).
          - El historial se recupera ANTES de persistir el mensaje actual.
          - El LLM recibe el historial formateado + query actual.
          - Los errores del RAG se propagan sin modificar.
        """

        # ---------------------------------------------------------------------
        # 1) Validar existencia de la conversación.
        # ---------------------------------------------------------------------
        if not self._conversations.conversation_exists(input_data.conversation_id):
            return AnswerQueryResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message=_MSG_CONVERSATION_NOT_FOUND,
                    resource=_RESOURCE_CONVERSATION,
                )
            )

        # ---------------------------------------------------------------------
        # 2) Recuperar historial reciente (ANTES de agregar el mensaje actual).
        # ---------------------------------------------------------------------
        history = self._fetch_history(
            input_data.conversation_id,
            limit=input_data.history_window,
        )

        # ---------------------------------------------------------------------
        # 3) Formatear historial para el LLM.
        # ---------------------------------------------------------------------
        llm_query_enhanced = format_conversation_for_prompt(
            history=history,
            current_query=input_data.query,
        )

        # ---------------------------------------------------------------------
        # 4) Persistir mensaje del usuario.
        # ---------------------------------------------------------------------
        user_message = ConversationMessage(role="user", content=input_data.query)
        self._persist_message_safe(input_data.conversation_id, user_message)

        # ---------------------------------------------------------------------
        # 5) Ejecutar AnswerQueryUseCase (flujo RAG puro).
        # ---------------------------------------------------------------------
        rag_input = AnswerQueryInput(
            query=input_data.query,  # Retrieval usa query original
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            llm_query=llm_query_enhanced,  # LLM recibe contexto conversacional
            top_k=input_data.top_k,
            use_mmr=input_data.use_mmr,
        )
        result = self._answer_query.execute(rag_input)

        # ---------------------------------------------------------------------
        # 6) Persistir mensaje del asistente (si hay respuesta exitosa).
        # ---------------------------------------------------------------------
        if result.result is not None and result.result.answer:
            assistant_message = ConversationMessage(
                role="assistant",
                content=result.result.answer,
            )
            self._persist_message_safe(input_data.conversation_id, assistant_message)

        return result

    # =========================================================================
    # Helpers privados
    # =========================================================================

    def _fetch_history(
        self,
        conversation_id: str,
        limit: int,
    ) -> list[ConversationMessage]:
        """
        Recupera el historial de la conversación (best-effort).

        Si falla, devuelve lista vacía para que el flujo continúe sin contexto.
        """
        try:
            return self._conversations.get_messages(conversation_id, limit=limit)
        except Exception:
            logger.warning(
                "Failed to fetch history. Continuing without context. conversation_id=%s",
                conversation_id,
            )
            return []

    def _persist_message_safe(
        self,
        conversation_id: str,
        message: ConversationMessage,
    ) -> None:
        """
        Persiste un mensaje (best-effort).

        Si falla, logueamos pero NO interrumpimos el flujo.
        Preferimos responder aunque no se guarde el historial.
        """
        try:
            self._conversations.append_message(conversation_id, message)
        except Exception:
            logger.exception(
                "Failed to persist message. conversation_id=%s role=%s",
                conversation_id,
                message.role,
            )
