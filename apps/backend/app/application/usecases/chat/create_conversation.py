"""
===============================================================================
USE CASE: Create Conversation (Initialize Chat Session)
===============================================================================

Name:
    Create Conversation Use Case

Business Goal:
    Iniciar una nueva sesión de conversación en un workspace, permitiendo al
    usuario tener múltiples hilos de chat independientes con contexto propio.

Why (Context / Intención):
    - Un usuario puede tener múltiples temas / investigaciones en paralelo.
    - El frontend necesita un ID de conversación para persistir historial.
    - Permite:
        * Historial persistente (el usuario refresca y su chat sigue ahí)
        * Contexto por conversación (futuro: query rewriting con historial)
        * Analytics / RLHF (analizar calidad de respuestas)

Security:
    - Requiere acceso de lectura al workspace (no expone workspaces ajenos).
    - La conversación se scoped por workspace_id.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    CreateConversationUseCase

Responsibilities:
    - Enforce workspace read access (policy + ACL si corresponde).
    - Crear una nueva conversación en el repositorio.
    - Opcionalmente, asociar título inicial o metadata.
    - Devolver CreateConversationResult con el ID de la conversación.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository, WorkspaceAclRepository:
        usados por resolve_workspace_for_read
    - ConversationRepository:
        create_conversation(workspace_id) -> conversation_id
    - Document results:
        DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    CreateConversationInput:
      - workspace_id: UUID
      - actor: WorkspaceActor | None
      - title: str | None (título opcional para la conversación)

Outputs:
    CreateConversationResult:
      - conversation_id: str | None
      - error: DocumentError | None

Error Mapping:
    - FORBIDDEN / NOT_FOUND:
        * resueltos por resolve_workspace_for_read
    - SERVICE_UNAVAILABLE:
        * falla ConversationRepository
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
_MSG_CREATE_FAILED: Final[str] = "Failed to create conversation."


@dataclass(frozen=True)
class CreateConversationInput:
    """
    DTO de entrada para crear conversación.

    Campos:
      - workspace_id: scope de la conversación
      - actor: actor para policy de lectura
      - title: título opcional (para mostrar en lista de conversaciones)
    """

    workspace_id: UUID
    actor: WorkspaceActor | None
    title: str | None = None


@dataclass(frozen=True)
class CreateConversationResult:
    """
    DTO de salida para crear conversación.

    Campos:
      - conversation_id: ID único de la conversación creada
      - error: error tipado si la operación falló
    """

    conversation_id: str | None = None
    error: DocumentError | None = None


class CreateConversationUseCase:
    """
    Use Case (Application Service / Command):
        Crea una nueva conversación en un workspace.
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

    def execute(self, input_data: CreateConversationInput) -> CreateConversationResult:
        """
        Crea una nueva conversación.

        Reglas:
          - Se requiere acceso de lectura al workspace (o ver sus documentos = chatear).
          - La conversación se asocia al workspace.
          - Retorna el ID único de la conversación.
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
            return CreateConversationResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Crear conversación.
        # ---------------------------------------------------------------------
        try:
            conversation_id = self._conversations.create_conversation()
        except Exception:
            logger.exception("Failed to create conversation")
            return CreateConversationResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message=_MSG_CREATE_FAILED,
                    resource=_RESOURCE_CONVERSATION,
                )
            )

        logger.info(
            "Conversation created. conversation_id=%s workspace_id=%s",
            conversation_id,
            input_data.workspace_id,
        )

        return CreateConversationResult(conversation_id=conversation_id)
