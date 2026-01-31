# =============================================================================
# FILE: application/usecases/chat/vote_answer.py
# =============================================================================
"""
===============================================================================
USE CASE: Vote Answer (RLHF Feedback)
===============================================================================

Name:
    Vote Answer Use Case

Business Goal:
    Permite a los usuarios dar feedback (👍/👎) sobre las respuestas del RAG,
    habilitando:
      - Métricas de calidad de respuestas
      - Data para futuro fine-tuning (RLHF)
      - Identificación de casos problemáticos
      - Mejora continua del sistema

Why (Context / Intención):
    - Sin feedback, no sabemos si el RAG responde bien o mal.
    - Los votos negativos identifican áreas de mejora.
    - Los votos positivos validan que el sistema funciona.
    - Esta data es oro puro para mejorar el retrieval y los prompts.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    VoteAnswerUseCase

Responsibilities:
    - Validar existencia de la conversación.
    - Validar existencia del mensaje votado.
    - Persistir el voto con metadata.
    - Registrar evento de auditoría.

Collaborators:
    - ConversationRepository: get_message, exists
    - FeedbackRepository: save_vote
    - AuditEventRepository: log

-------------------------------------------------------------------------------
INPUTS / OUTPUTS
-------------------------------------------------------------------------------
Inputs:
    VoteAnswerInput:
      - conversation_id: str
      - message_index: int (índice del mensaje en la conversación)
      - vote: "up" | "down" | "neutral"
      - comment: Optional[str]
      - tags: List[str] (ej: ["incorrect", "incomplete", "off-topic"])
      - actor: WorkspaceActor

Outputs:
    VoteAnswerResult:
      - success: bool
      - error: DocumentError | None
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final, List, Optional, Protocol
from uuid import UUID

from ....domain.value_objects import FeedbackVote
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import DocumentError, DocumentErrorCode

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_RESOURCE_CONVERSATION: Final[str] = "Conversation"
_RESOURCE_MESSAGE: Final[str] = "Message"
_RESOURCE_FEEDBACK: Final[str] = "Feedback"

_MSG_CONVERSATION_NOT_FOUND: Final[str] = "Conversation not found."
_MSG_MESSAGE_NOT_FOUND: Final[str] = "Message not found at specified index."
_MSG_INVALID_VOTE: Final[str] = "Invalid vote type."
_MSG_ALREADY_VOTED: Final[str] = "User has already voted on this message."


# -----------------------------------------------------------------------------
# Ports (Protocols)
# -----------------------------------------------------------------------------
class FeedbackRepository(Protocol):
    """Port for feedback persistence."""

    def save_vote(
        self,
        *,
        conversation_id: str,
        message_index: int,
        user_id: UUID,
        vote: str,
        comment: Optional[str],
        tags: List[str],
        created_at: datetime,
    ) -> str:
        """
        Persists a vote and returns the vote ID.

        Raises:
            DuplicateVoteError: If user already voted on this message.
        """
        ...

    def get_vote(
        self, *, conversation_id: str, message_index: int, user_id: UUID
    ) -> Optional[dict]:
        """Returns existing vote if any."""
        ...


class ConversationPort(Protocol):
    """Minimal conversation repository port for this use case."""

    def conversation_exists(self, conversation_id: str) -> bool: ...

    def get_message_count(self, conversation_id: str) -> int: ...


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class VoteAnswerInput:
    """
    DTO de entrada para votar una respuesta.

    Campos:
      - conversation_id: ID de la conversación
      - message_index: Índice del mensaje a votar (0-based)
      - vote: Tipo de voto ("up", "down", "neutral")
      - comment: Comentario opcional
      - tags: Tags de categorización
      - actor: Actor que vota (para user_id)
    """

    conversation_id: str
    message_index: int
    vote: str
    actor: WorkspaceActor
    comment: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VoteAnswerResult:
    """
    DTO de salida del caso de uso.

    Campos:
      - success: True si el voto se guardó correctamente
      - vote_id: ID del voto creado (si success)
      - error: Error si falló
    """

    success: bool = False
    vote_id: Optional[str] = None
    error: Optional[DocumentError] = None


# -----------------------------------------------------------------------------
# Use Case
# -----------------------------------------------------------------------------
class VoteAnswerUseCase:
    """
    Use Case: Registrar feedback del usuario sobre una respuesta RAG.

    Estrategia:
        1) Validar conversación existe.
        2) Validar mensaje existe en la conversación.
        3) Validar que el usuario no haya votado ya (idempotencia).
        4) Persistir el voto.
        5) Loggear para analytics.
    """

    def __init__(
        self,
        conversation_repository: ConversationPort,
        feedback_repository: FeedbackRepository,
    ) -> None:
        self._conversations = conversation_repository
        self._feedback = feedback_repository

    def execute(self, input_data: VoteAnswerInput) -> VoteAnswerResult:
        """
        Ejecuta el registro de voto.

        Reglas:
          - La conversación debe existir.
          - El mensaje debe existir (índice válido).
          - El voto debe ser válido ("up", "down", "neutral").
          - Un usuario solo puede votar una vez por mensaje (idempotente).
        """

        # ---------------------------------------------------------------------
        # 1) Validar voto
        # ---------------------------------------------------------------------
        try:
            feedback_vote = FeedbackVote(
                vote=input_data.vote,
                comment=input_data.comment,
                tags=tuple(input_data.tags),
            )
        except ValueError as e:
            return VoteAnswerResult(
                error=DocumentError(
                    code=DocumentErrorCode.VALIDATION_ERROR,
                    message=str(e),
                    resource=_RESOURCE_FEEDBACK,
                )
            )

        # ---------------------------------------------------------------------
        # 2) Validar conversación existe
        # ---------------------------------------------------------------------
        if not self._conversations.conversation_exists(input_data.conversation_id):
            return VoteAnswerResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message=_MSG_CONVERSATION_NOT_FOUND,
                    resource=_RESOURCE_CONVERSATION,
                )
            )

        # ---------------------------------------------------------------------
        # 3) Validar mensaje existe
        # ---------------------------------------------------------------------
        message_count = self._conversations.get_message_count(
            input_data.conversation_id
        )
        if input_data.message_index < 0 or input_data.message_index >= message_count:
            return VoteAnswerResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message=_MSG_MESSAGE_NOT_FOUND,
                    resource=_RESOURCE_MESSAGE,
                )
            )

        # ---------------------------------------------------------------------
        # 4) Verificar voto previo (idempotencia)
        # ---------------------------------------------------------------------
        user_id = input_data.actor.user_id
        existing_vote = self._feedback.get_vote(
            conversation_id=input_data.conversation_id,
            message_index=input_data.message_index,
            user_id=user_id,
        )
        if existing_vote is not None:
            # Ya votó - retornamos success=True con el vote_id existente
            logger.info(
                "User already voted on message. Returning existing vote.",
                extra={
                    "conversation_id": input_data.conversation_id,
                    "message_index": input_data.message_index,
                    "user_id": str(user_id),
                },
            )
            return VoteAnswerResult(
                success=True,
                vote_id=existing_vote.get("vote_id"),
            )

        # ---------------------------------------------------------------------
        # 5) Persistir voto
        # ---------------------------------------------------------------------
        try:
            vote_id = self._feedback.save_vote(
                conversation_id=input_data.conversation_id,
                message_index=input_data.message_index,
                user_id=user_id,
                vote=feedback_vote.vote,
                comment=feedback_vote.comment,
                tags=list(feedback_vote.tags),
                created_at=datetime.now(timezone.utc),
            )
        except Exception:
            logger.exception(
                "Failed to save vote",
                extra={
                    "conversation_id": input_data.conversation_id,
                    "message_index": input_data.message_index,
                },
            )
            return VoteAnswerResult(
                error=DocumentError(
                    code=DocumentErrorCode.INTERNAL_ERROR,
                    message="Failed to save vote.",
                    resource=_RESOURCE_FEEDBACK,
                )
            )

        logger.info(
            "Vote saved successfully",
            extra={
                "vote_id": vote_id,
                "conversation_id": input_data.conversation_id,
                "message_index": input_data.message_index,
                "vote": feedback_vote.vote,
                "user_id": str(user_id),
            },
        )

        return VoteAnswerResult(success=True, vote_id=vote_id)
