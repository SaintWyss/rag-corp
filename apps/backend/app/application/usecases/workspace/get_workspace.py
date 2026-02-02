"""
===============================================================================
USE CASE: Get Workspace
===============================================================================

Name:
    Get Workspace Use Case

Business Goal:
    Obtener un workspace por ID, respetando la política de acceso de lectura.
    Si el workspace no existe o está archivado, se responde como NOT_FOUND.

Why (Context / Intención):
    - Un workspace puede ser visible bajo distintas reglas (PRIVATE / SHARED / ORG_READ).
    - El acceso de lectura depende del actor y, en caso de SHARED, del ACL.
    - Este caso de uso centraliza el control de acceso (no “filtrar” desde API).

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    GetWorkspaceUseCase

Responsibilities:
    - Recuperar el workspace por ID desde repositorio.
    - Rechazar workspaces inexistentes o archivados (soft-deleted).
    - Si el workspace es SHARED, cargar ACL para evaluar acceso.
    - Evaluar política de lectura (can_read_workspace) con datos necesarios.
    - Devolver WorkspaceResult tipado con workspace o error.

Collaborators:
    - WorkspaceRepository:
        get_workspace(workspace_id) -> Workspace | None
    - WorkspaceAclRepository:
        list_workspace_acl(workspace_id) -> list[UUID]
    - workspace_policy:
        can_read_workspace(workspace, actor, shared_user_ids=...) -> bool
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
        - workspace existe pero está archivado (no visible como activo)
    - FORBIDDEN:
        - actor no tiene permiso de lectura según policy (y ACL si corresponde)
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from ....domain.entities import WorkspaceVisibility
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_read_workspace
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class GetWorkspaceUseCase:
    """
    Use Case (Application Service / Query):
        Lee un workspace por ID aplicando reglas de acceso de lectura.

    Nota:
        Aunque es una operación "get", mantiene responsabilidad de seguridad.
        Los repositorios entregan datos; la policy decide acceso.
    """

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ) -> None:
        # Naming explícito: mejora legibilidad y evita "repository" genérico.
        self._workspaces = workspace_repository
        self._acls = acl_repository

    def execute(
        self, workspace_id: UUID, actor: WorkspaceActor | None
    ) -> WorkspaceResult:
        """
        Obtiene un workspace por ID si el actor tiene acceso de lectura.

        Precondiciones:
          - workspace_id válido
          - actor puede ser None (se considera no autorizado)

        Poscondiciones (si SUCCESS):
          - Se devuelve el workspace solicitado (no archivado)
        """

        # ---------------------------------------------------------------------
        # 1) Load workspace (estado actual).
        # ---------------------------------------------------------------------
        workspace = self._workspaces.get_workspace(workspace_id)

        # ---------------------------------------------------------------------
        # 2) Si no existe o está archivado -> NOT_FOUND.
        # ---------------------------------------------------------------------
        # Se responde NOT_FOUND para evitar filtrar información de existencia
        # en casos donde el caller no debería enterarse del resource.
        if workspace is None or workspace.is_archived:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 3) Si es SHARED, cargar ACL para evaluar permisos.
        # ---------------------------------------------------------------------
        # can_read_workspace requiere "shared_user_ids" para la regla SHARED.
        shared_user_ids: list[UUID] | None = None
        if workspace.visibility == WorkspaceVisibility.SHARED:
            shared_user_ids = self._acls.list_workspace_acl(workspace.id)

        # ---------------------------------------------------------------------
        # 4) Evaluar política de lectura.
        # ---------------------------------------------------------------------
        if not can_read_workspace(workspace, actor, shared_user_ids=shared_user_ids):
            return self._forbidden()

        # ---------------------------------------------------------------------
        # 5) Retornar workspace.
        # ---------------------------------------------------------------------
        return WorkspaceResult(workspace=workspace)

    # =========================================================================
    # Helpers privados: reducen duplicación y mantienen execute() legible.
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
