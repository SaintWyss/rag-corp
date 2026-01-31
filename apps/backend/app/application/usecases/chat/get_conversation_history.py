"""
===============================================================================
USE CASE: Get Conversation History (Retrieve Chat Messages)
===============================================================================

Name:
    Get Conversation History Use Case

Business Goal:
    Obtener el historial de mensajes de una conversación existente, permitiendo:
      - Restaurar el chat cuando el usuario vuelve a la página
      - Mostrar el historial completo o las últimas N entradas
      - Base para query rewriting con contexto de conversación

Why (Context / Intención):
    - El usuario necesita ver su historial cuando refresca / regresa.
    - El frontend puede pedir solo los últimos N mensajes por performance.
    - Futuro: el historial se puede usar para rewrite del query con contexto.

Security:
    - Requiere acceso de lectura al workspace.
    - Solo retorna mensajes de conversaciones existentes (valida existencia).

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    GetConversationHistoryUseCase

Responsibilities:
    - Enforce workspace read access (policy + ACL si corresponde).
    - Validar que la conversación existe.
    - Recuperar mensajes del repositorio (opcionalmente limitados).
    - Devolver GetConversationHistoryResult con lista de mensajes.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository, WorkspaceAclRepository:
        usados por resolve_workspace_for_read
    - ConversationRepository:
        conversation_exists(conversation_id) -> bool
        get_messages(conversation_id, limit) -> list[ConversationMessage]
    - Document results:
        DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    GetConversationHistoryInput:
      - workspace_id: UUID
      - conversation_id: str
      - actor: WorkspaceActor | None
      - limit: int | None (None = todos los mensajes)

Outputs:
    GetConversationHistoryResult:
      - messages: list[ConversationMessage]
      - error: DocumentError | None

Error Mapping:
    - NOT_FOUND:
        * conversación no existe
    - FORBIDDEN / NOT_FOUND (workspace):
        * resueltos por resolve_workspace_for_read
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final
from uuid import UUID

from ....domain.entities import ConversationMessage
from ....domain.repositories import (
    ConversationRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import DocumentError, DocumentErrorCode
from ..workspace.workspace_access import resolve_workspace_for_read

_RESOURCE_CONVERSATION: Final[str] = "Conversation"
_MSG_NOT_FOUND: Final[str] = "Conversation not found."


@dataclass(frozen=True)
class GetConversationHistoryInput:
    """
    DTO de entrada para obtener historial de conversación.

    Campos:
      - workspace_id: scope del workspace
      - conversation_id: ID de la conversación
      - actor: actor para policy de lectura
      - limit: límite de mensajes (None = todos)
    """

    workspace_id: UUID
    conversation_id: str
    actor: WorkspaceActor | None
    limit: int | None = None


@dataclass(frozen=True)
class GetConversationHistoryResult:
    """
    DTO de salida para historial de conversación.

    Campos:
      - messages: lista de mensajes ordenados cronológicamente
      - error: error tipado si la operación falló
    """

    messages: list[ConversationMessage] = field(default_factory=list)
    error: DocumentError | None = None


class GetConversationHistoryUseCase:
    """
    Use Case (Application Service / Query):
        Recupera el historial de mensajes de una conversación.
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

    def execute(
        self, input_data: GetConversationHistoryInput
    ) -> GetConversationHistoryResult:
        """
        Recupera el historial de la conversación.

        Reglas:
          - Se requiere acceso de lectura al workspace.
          - La conversación debe existir.
          - Si no existe, devuelve NOT_FOUND.
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
            return GetConversationHistoryResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Validar existencia de la conversación.
        # ---------------------------------------------------------------------
        if not self._conversations.conversation_exists(input_data.conversation_id):
            return GetConversationHistoryResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message=_MSG_NOT_FOUND,
                    resource=_RESOURCE_CONVERSATION,
                )
            )

        # ---------------------------------------------------------------------
        # 3) Recuperar mensajes.
        # ---------------------------------------------------------------------
        messages = self._conversations.get_messages(
            input_data.conversation_id,
            limit=input_data.limit,
        )

        return GetConversationHistoryResult(messages=messages)
