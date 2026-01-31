"""
===============================================================================
USE CASE: Answer Query With History (RAG + Conversation Persistence)
===============================================================================

Name:
    Answer Query With History Use Case

Business Goal:
    Responder una pregunta del usuario usando RAG Y persistir la interacción
    en el historial de conversación, permitiendo:
      - Historial persistente (el usuario refresca y su chat sigue ahí)
      - Base para query rewriting con contexto de conversación (futuro)
      - Analytics / RLHF (analizar calidad de respuestas)

Why (Context / Intención):
    - En un flujo de chat real, necesitamos guardar cada mensaje.
    - El AnswerQueryUseCase es stateless (no persiste nada).
    - Este use case orquesta:
        1) Append mensaje del usuario
        2) Ejecutar AnswerQueryUseCase
        3) Append mensaje del asistente con metadata

    - Separation of Concerns:
        * AnswerQueryUseCase: lógica pura de RAG (retrieval + generation)
        * Este use case: orquestación de persistencia + llamada a RAG

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    AnswerQueryWithHistoryUseCase

Responsibilities:
    - Validar existencia de la conversación.
    - Persistir mensaje del usuario antes de procesar.
    - Delegar a AnswerQueryUseCase para el flujo RAG.
    - Persistir mensaje del asistente después de obtener respuesta.
    - Devolver el resultado del RAG (transparente para el llamador).

Collaborators:
    - ConversationRepository:
        conversation_exists(conversation_id) -> bool
        append_message(conversation_id, message) -> None
    - AnswerQueryUseCase:
        execute(AnswerQueryInput) -> AnswerQueryResult
    - Document results:
        AnswerQueryResult / DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    AnswerQueryWithHistoryInput:
      - conversation_id: str
      - query: str
      - workspace_id: UUID
      - actor: WorkspaceActor | None
      - llm_query: Optional[str]
      - top_k: int
      - use_mmr: bool

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
from typing import Final, Optional
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

logger = logging.getLogger(__name__)

_RESOURCE_CONVERSATION: Final[str] = "Conversation"
_MSG_CONVERSATION_NOT_FOUND: Final[str] = "Conversation not found."

_DEFAULT_TOP_K: Final[int] = 5


@dataclass(frozen=True)
class AnswerQueryWithHistoryInput:
    """
    DTO de entrada para AnswerQuery con persistencia de historial.

    Campos:
      - conversation_id: ID de la conversación existente
      - query: pregunta del usuario
      - workspace_id: scope del retrieval
      - actor: actor para policy de acceso
      - llm_query: override opcional del query para el LLM
      - top_k: cantidad de chunks a recuperar
      - use_mmr: retrieval diverso (MMR) vs similarity
    """

    conversation_id: str
    query: str
    workspace_id: UUID
    actor: WorkspaceActor | None
    llm_query: Optional[str] = None
    top_k: int = _DEFAULT_TOP_K
    use_mmr: bool = False


class AnswerQueryWithHistoryUseCase:
    """
    Use Case (Application Service / Orchestration):
        Orquesta el flujo de RAG CON persistencia de historial de conversación.

    Estrategia:
        1) Validar conversación existe.
        2) Persistir mensaje del usuario.
        3) Ejecutar AnswerQueryUseCase.
        4) Persistir mensaje del asistente (si éxito).
        5) Devolver resultado (transparente).
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
        Ejecuta el flujo RAG con persistencia de historial.

        Reglas:
          - La conversación debe existir (pre-condición).
          - Se guarda el mensaje del usuario ANTES de llamar al RAG.
          - Se guarda el mensaje del asistente DESPUÉS si hay respuesta.
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
        # 2) Persistir mensaje del usuario.
        # ---------------------------------------------------------------------
        user_message = ConversationMessage(role="user", content=input_data.query)
        try:
            self._conversations.append_message(input_data.conversation_id, user_message)
        except Exception:
            logger.exception(
                "Failed to persist user message. conversation_id=%s",
                input_data.conversation_id,
            )
            # No fallamos: preferimos responder aunque no se guarde el historial.

        # ---------------------------------------------------------------------
        # 3) Ejecutar AnswerQueryUseCase (flujo RAG puro).
        # ---------------------------------------------------------------------
        rag_input = AnswerQueryInput(
            query=input_data.query,
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            llm_query=input_data.llm_query,
            top_k=input_data.top_k,
            use_mmr=input_data.use_mmr,
        )
        result = self._answer_query.execute(rag_input)

        # ---------------------------------------------------------------------
        # 4) Persistir mensaje del asistente (si hay respuesta exitosa).
        # ---------------------------------------------------------------------
        if result.result is not None and result.result.answer:
            assistant_message = ConversationMessage(
                role="assistant",
                content=result.result.answer,
            )
            try:
                self._conversations.append_message(
                    input_data.conversation_id, assistant_message
                )
            except Exception:
                logger.exception(
                    "Failed to persist assistant message. conversation_id=%s",
                    input_data.conversation_id,
                )
                # No fallamos: la respuesta ya se generó.

        return result
