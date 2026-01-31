"""
===============================================================================
USE CASE: Share Workspace (SHARED + ACL Replacement)
===============================================================================

Name:
    Share Workspace Use Case

Business Goal:
    Compartir un workspace con una lista explícita de usuarios:
      - Cambiar visibilidad a SHARED
      - Reemplazar por completo el ACL del workspace con los user_ids provistos

Why (Context / Intención):
    - SHARED representa un workspace visible solo para miembros explícitos.
    - El ACL es la fuente de verdad de “quién puede ver” en modo SHARED.
    - Se utiliza "replace" para que la operación sea declarativa:
        * el cliente envía el estado deseado del ACL
        * el sistema lo hace realidad sin diffs parciales

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ShareWorkspaceUseCase

Responsibilities:
    - Validar que la lista de user_ids no esté vacía.
    - Obtener el workspace por ID y validar que no esté archivado.
    - Validar permisos para administrar ACL (policy: can_manage_acl).
    - Reemplazar el ACL del workspace con la lista provista (idempotente a nivel datos).
    - Asegurar visibilidad SHARED en el workspace.
    - Devolver WorkspaceResult tipado con workspace actualizado o error estable.

Collaborators:
    - WorkspaceRepository:
        get_workspace(workspace_id) -> Workspace | None
        update_workspace(workspace_id, visibility=...) -> Workspace | None
    - WorkspaceAclRepository:
        replace_workspace_acl(workspace_id, user_ids) -> None
    - workspace_policy:
        can_manage_acl(workspace, actor) -> bool
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
    - user_ids: list[UUID]     (debe ser no vacía)

Outputs:
    - WorkspaceResult:
        - workspace: Workspace | None
        - error: WorkspaceError | None

Error Mapping:
    - VALIDATION_ERROR:
        - user_ids vacío
    - NOT_FOUND:
        - workspace no existe
        - workspace está archivado
        - race condition: falla update (ya no existe)
    - FORBIDDEN:
        - actor sin permiso para administrar ACL
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from ....domain.entities import WorkspaceVisibility
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_manage_acl
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class ShareWorkspaceUseCase:
    """
    Use Case (Application Service / Command):
        Comparte un workspace estableciendo visibilidad SHARED y reemplazando
        el ACL con una lista de usuarios explícitos.
    """

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ) -> None:
        self._workspaces = workspace_repository
        self._acls = acl_repository

    def execute(
        self,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
        *,
        user_ids: list[UUID],
    ) -> WorkspaceResult:
        """
        Comparte el workspace.

        Reglas:
          - El ACL no puede ser vacío: un SHARED sin miembros no tiene sentido
            y produciría un recurso inaccesible.
          - El workspace debe existir y no estar archivado.
          - Se requiere permiso para administrar ACL (can_manage_acl).
          - Se reemplaza completamente el ACL y luego se fuerza visibilidad SHARED.

        Nota (consistencia):
          - Idealmente "replace ACL" + "update visibility" deberían ser atómicos
            bajo una transacción / UnitOfWork. Aquí se ejecutan secuencialmente.
        """

        # ---------------------------------------------------------------------
        # 1) Validar entrada.
        # ---------------------------------------------------------------------
        # Un SHARED sin miembros deja el recurso efectivamente inaccesible.
        if not user_ids:
            return self._validation_error("Workspace ACL cannot be empty.")

        # ---------------------------------------------------------------------
        # 2) Cargar workspace y validar estado.
        # ---------------------------------------------------------------------
        workspace = self._workspaces.get_workspace(workspace_id)
        if workspace is None or workspace.is_archived:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 3) Autorización: se requiere permiso para manejar ACL.
        # ---------------------------------------------------------------------
        if not can_manage_acl(workspace, actor):
            return self._forbidden()

        # ---------------------------------------------------------------------
        # 4) Reemplazar ACL.
        # ---------------------------------------------------------------------
        # Se usa "replace" para que el comando sea declarativo e idempotente:
        #   - si el cliente repite el request, el estado final del ACL es el mismo.
        self._acls.replace_workspace_acl(workspace_id, user_ids)

        # ---------------------------------------------------------------------
        # 5) Asegurar visibilidad SHARED.
        # ---------------------------------------------------------------------
        # Si ya estaba SHARED, esto es idempotente a nivel intención; el repo puede
        # igual devolver la entidad actualizada.
        updated = self._workspaces.update_workspace(
            workspace_id,
            visibility=WorkspaceVisibility.SHARED,
        )

        if updated is None:
            # Race condition: el workspace pudo desaparecer entre lectura y escritura.
            return self._not_found()

        return WorkspaceResult(workspace=updated)

    # =========================================================================
    # Helpers privados: resultados consistentes y código más legible.
    # =========================================================================

    @staticmethod
    def _validation_error(message: str) -> WorkspaceResult:
        """Resultado consistente para VALIDATION_ERROR."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.VALIDATION_ERROR,
                message=message,
            )
        )

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
