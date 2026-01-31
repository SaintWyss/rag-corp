"""
===============================================================================
USE CASE: Clear Conversation (Delete Chat History)
===============================================================================

Name:
    Clear Conversation Use Case

Business Goal:
    Limpiar el historial de una conversación, permitiendo al usuario:
      - Empezar de cero sin crear una nueva conversación
      - Limpiar datos sensibles de un chat
      - Reset para cambiar de tema en la misma "sesión"

Why (Context / Intención):
    - El usuario puede querer borrar información sensible.
    - El frontend puede ofrecer un botón "Limpiar chat".
    - Mantiene el conversation_id pero borra mensajes (útil para analytics).

Security:
    - Requiere acceso de lectura al workspace (el usuario "ve" la conversación).
    - Solo puede limpiar conversaciones existentes.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ClearConversationUseCase

Responsibilities:
    - Enforce workspace read access (policy + ACL si corresponde).
    - Validar existencia de la conversación.
    - Eliminar todos los mensajes de la conversación.
    - Devolver ClearConversationResult indicando éxito.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository, WorkspaceAclRepository:
        usados por resolve_workspace_for_read
    - ConversationRepository:
        conversation_exists(conversation_id) -> bool
        clear_messages(conversation_id) -> None

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    ClearConversationInput:
      - workspace_id: UUID
      - conversation_id: str
      - actor: WorkspaceActor | None

Outputs:
    ClearConversationResult:
      - cleared: bool
      - error: DocumentError | None

Error Mapping:
    - NOT_FOUND:
        * conversación no existe
    - FORBIDDEN / NOT_FOUND (workspace):
        * resueltos por resolve_workspace_for_read
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from ....domain.repositories import (
    ConversationRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import DocumentError, DocumentErrorCode
from ..workspace.workspace_access import resolve_workspace_for_read

logger = logging.getLogger(__name__)

_RESOURCE_CONVERSATION: Final[str] = "Conversation"
_MSG_NOT_FOUND: Final[str] = "Conversation not found."


@dataclass(frozen=True)
class ClearConversationInput:
    """
    DTO de entrada para limpiar conversación.

    Campos:
      - workspace_id: scope del workspace
      - conversation_id: ID de la conversación a limpiar
      - actor: actor para policy de lectura
    """

    workspace_id: UUID
    conversation_id: str
    actor: WorkspaceActor | None


@dataclass(frozen=True)
class ClearConversationResult:
    """
    DTO de salida para limpiar conversación.

    Campos:
      - cleared: True si la conversación fue limpiada exitosamente
      - error: error tipado si la operación falló
    """

    cleared: bool = False
    error: DocumentError | None = None


class ClearConversationUseCase:
    """
    Use Case (Application Service / Command):
        Limpia el historial de una conversación.
    """

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ) -> None:
        self._conversations = conversation_repository
        self._workspaces = workspace_repository
        self._acls = acl_repository

    def execute(self, input_data: ClearConversationInput) -> ClearConversationResult:
        """
        Limpia el historial de la conversación.

        Reglas:
          - Se requiere acceso de lectura al workspace.
          - La conversación debe existir.
          - Todos los mensajes son eliminados.
        """

        # ---------------------------------------------------------------------
        # 1) Enforce acceso al workspace (read).
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_read(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self._workspaces,
            acl_repository=self._acls,
        )
        if workspace_error is not None:
            return ClearConversationResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Validar existencia de la conversación.
        # ---------------------------------------------------------------------
        if not self._conversations.conversation_exists(input_data.conversation_id):
            return ClearConversationResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message=_MSG_NOT_FOUND,
                    resource=_RESOURCE_CONVERSATION,
                )
            )

        # ---------------------------------------------------------------------
        # 3) Limpiar mensajes.
        # ---------------------------------------------------------------------
        try:
            self._conversations.clear_messages(input_data.conversation_id)
        except Exception:
            logger.exception(
                "Failed to clear conversation. conversation_id=%s",
                input_data.conversation_id,
            )
            return ClearConversationResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Failed to clear conversation.",
                    resource=_RESOURCE_CONVERSATION,
                )
            )

        logger.info(
            "Conversation cleared. conversation_id=%s workspace_id=%s",
            input_data.conversation_id,
            input_data.workspace_id,
        )

        return ClearConversationResult(cleared=True)
