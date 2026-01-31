"""
===============================================================================
USE CASE: Publish Workspace (ORG_READ)
===============================================================================

Name:
    Publish Workspace Use Case

Business Goal:
    Publicar un workspace dentro de la organización estableciendo su visibilidad
    a ORG_READ, permitiendo lectura a actores con alcance organizacional.

Why (Context / Intención):
    - Un workspace puede comenzar como PRIVATE y luego hacerse accesible a la
      organización (ORG_READ) cuando el owner/admin lo decide.
    - Este caso de uso asegura:
        * existencia del workspace
        * no estar archivado (soft-deleted)
        * permiso de escritura (write access)
        * actualización idempotente (si ya está ORG_READ, no re-escribe)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    PublishWorkspaceUseCase

Responsibilities:
    - Obtener workspace por ID.
    - Rechazar workspaces inexistentes o archivados.
    - Validar permisos de escritura con policy (can_write_workspace).
    - Aplicar transición de visibilidad a ORG_READ.
    - Comportamiento idempotente: si ya está ORG_READ, devolver estado actual.
    - Devolver WorkspaceResult tipado con workspace o error estable.

Collaborators:
    - WorkspaceRepository:
        get_workspace(workspace_id) -> Workspace | None
        update_workspace(workspace_id, visibility=...) -> Workspace | None
    - workspace_policy:
        can_write_workspace(workspace, actor) -> bool
    - Domain entities:
        WorkspaceVisibility
    - workspace_results:
        WorkspaceResult / WorkspaceError / WorkspaceErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - workspace_id: UUID
    - actor: WorkspaceActor | None

Outputs:
    - WorkspaceResult:
        - workspace: Workspace | None
        - error: WorkspaceError | None

Error Mapping:
    - NOT_FOUND:
        - workspace no existe
        - workspace está archivado
        - race condition: falla update (ya no existe)
    - FORBIDDEN:
        - actor sin permiso de escritura
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from ....domain.entities import WorkspaceVisibility
from ....domain.repositories import WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_write_workspace
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class PublishWorkspaceUseCase:
    """
    Use Case (Application Service / Command):
        Cambia la visibilidad de un workspace a ORG_READ, aplicando policy de
        escritura y devolviendo un resultado tipado.
    """

    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        # Naming explícito: evita "repository" genérico.
        self._workspaces = workspace_repository

    def execute(
        self, workspace_id: UUID, actor: WorkspaceActor | None
    ) -> WorkspaceResult:
        """
        Publica un workspace para lectura organizacional (ORG_READ).

        Precondiciones:
          - workspace_id válido
          - actor puede ser None (se trata como no autorizado)

        Poscondiciones (si SUCCESS):
          - workspace.visibility == WorkspaceVisibility.ORG_READ
        """

        # ---------------------------------------------------------------------
        # 1) Obtener workspace actual.
        # ---------------------------------------------------------------------
        workspace = self._workspaces.get_workspace(workspace_id)

        # ---------------------------------------------------------------------
        # 2) Validar existencia y estado (no archivado).
        # ---------------------------------------------------------------------
        if workspace is None or workspace.is_archived:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 3) Autorización: se requiere permiso de escritura.
        # ---------------------------------------------------------------------
        if not can_write_workspace(workspace, actor):
            return self._forbidden()

        # ---------------------------------------------------------------------
        # 4) Idempotencia: si ya está publicado, devolvemos el estado actual.
        # ---------------------------------------------------------------------
        if workspace.visibility == WorkspaceVisibility.ORG_READ:
            return WorkspaceResult(workspace=workspace)

        # ---------------------------------------------------------------------
        # 5) Persistir el cambio de visibilidad.
        # ---------------------------------------------------------------------
        updated = self._workspaces.update_workspace(
            workspace_id,
            visibility=WorkspaceVisibility.ORG_READ,
        )

        if updated is None:
            # Race condition: el workspace pudo desaparecer entre read y write.
            return self._not_found()

        return WorkspaceResult(workspace=updated)

    # =========================================================================
    # Helpers privados: errores consistentes y código más legible.
    # =========================================================================

    @staticmethod
    def _not_found() -> WorkspaceResult:
        """Resultado consistente para NOT_FOUND."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.NOT_FOUND,
                message="Workspace not found.",
            )
        )

    @staticmethod
    def _forbidden() -> WorkspaceResult:
        """Resultado consistente para FORBIDDEN."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.FORBIDDEN,
                message="Access denied.",
            )
        )
