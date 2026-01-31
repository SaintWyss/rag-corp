"""
===============================================================================
USE CASE: Update Workspace (Name / Description)
===============================================================================

Name:
    Update Workspace Use Case

Business Goal:
    Actualizar los campos editables de un workspace (name y/o description)
    respetando la política de acceso (write permission) y garantizando unicidad
    del nombre por owner.

Why (Context / Intención):
    - Permite mantener la información del workspace actualizada sin permitir
      cambios inconsistentes o no autorizados.
    - Invariantes:
        * al menos un campo debe ser provisto
        * si se actualiza name, no puede ser vacío (luego de normalizar)
        * si se cambia name, debe ser único para el mismo owner
        * no se puede modificar un workspace archivado

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    UpdateWorkspaceUseCase

Responsibilities:
    - Validar que haya al menos un campo para actualizar.
    - Normalizar y validar el nombre (si se provee).
    - Cargar workspace y validar que exista y no esté archivado.
    - Validar autorización (policy: can_write_workspace).
    - Validar unicidad del nombre por owner (si se modifica).
    - Persistir la actualización y devolver WorkspaceResult tipado.

Collaborators:
    - WorkspaceRepository:
        get_workspace(workspace_id) -> Workspace | None
        get_workspace_by_owner_and_name(owner_id, name) -> Workspace | None
        update_workspace(workspace_id, name=?, description=?) -> Workspace | None
    - workspace_policy:
        can_write_workspace(workspace, actor) -> bool
    - workspace_results:
        WorkspaceResult / WorkspaceError / WorkspaceErrorCode
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from ....domain.repositories import WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_write_workspace
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class UpdateWorkspaceUseCase:
    """
    Use Case (Application Service / Command):
        Actualiza atributos editables de un workspace aplicando validaciones
        de negocio, unicidad y policy de escritura.
    """

    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self._workspaces = workspace_repository

    def execute(
        self,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> WorkspaceResult:
        """
        Actualiza name y/o description.

        Reglas:
          - Debe proveerse al menos un campo (name o description).
          - name, si se provee, no puede quedar vacío luego de normalizar.
          - Cambiar name requiere que sea único para el mismo owner.
          - Se requiere permiso de escritura.
          - Workspaces archivados no son editables.
        """

        # ---------------------------------------------------------------------
        # 1) Validar "no-op": al menos un campo debe venir.
        # ---------------------------------------------------------------------
        if name is None and description is None:
            return self._validation_error("No fields provided to update.")

        # ---------------------------------------------------------------------
        # 2) Normalizar y validar el nombre si fue provisto.
        # ---------------------------------------------------------------------
        normalized_name = self._normalize_name(name) if name is not None else None
        if name is not None and not normalized_name:
            return self._validation_error("Workspace name cannot be empty.")

        # ---------------------------------------------------------------------
        # 3) Cargar workspace y validar estado.
        # ---------------------------------------------------------------------
        workspace = self._workspaces.get_workspace(workspace_id)
        if workspace is None or workspace.is_archived:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 4) Autorización: permiso de escritura requerido.
        # ---------------------------------------------------------------------
        if not can_write_workspace(workspace, actor):
            return self._forbidden()

        # ---------------------------------------------------------------------
        # 5) Validar unicidad del nombre por owner si realmente cambia.
        # ---------------------------------------------------------------------
        # Se evita consultar si:
        #   - name no se envía
        #   - name normalizado es igual al actual (no hay cambio real)
        if normalized_name is not None and normalized_name != workspace.name:
            if self._name_conflicts_for_owner(
                owner_user_id=workspace.owner_user_id,
                workspace_id=workspace_id,
                new_name=normalized_name,
            ):
                return self._conflict("Workspace name already exists for owner.")

        # ---------------------------------------------------------------------
        # 6) Persistir actualización.
        # ---------------------------------------------------------------------
        updated = self._workspaces.update_workspace(
            workspace_id,
            name=normalized_name,
            description=description,
        )

        if updated is None:
            # Race condition: puede desaparecer entre read y write.
            return self._not_found()

        return WorkspaceResult(workspace=updated)

    # =========================================================================
    # Helpers privados: encapsulan reglas y reducen duplicación.
    # =========================================================================

    @staticmethod
    def _normalize_name(raw_name: str | None) -> str:
        """
        Normaliza el nombre para consistencia.

        - strip(): elimina espacios al principio/fin.
        - (Opcional futuro) colapsar espacios internos, validar longitud, etc.
        """
        return (raw_name or "").strip()

    def _name_conflicts_for_owner(
        self,
        *,
        owner_user_id: UUID,
        workspace_id: UUID,
        new_name: str,
    ) -> bool:
        """
        Devuelve True si existe otro workspace del mismo owner con el mismo name.

        Importante:
          - Si el repo devuelve el mismo workspace, no es conflicto (rename al mismo).
        """
        existing = self._workspaces.get_workspace_by_owner_and_name(
            owner_user_id, new_name
        )
        return existing is not None and existing.id != workspace_id

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

    @staticmethod
    def _conflict(message: str) -> WorkspaceResult:
        """Resultado consistente para CONFLICT."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.CONFLICT,
                message=message,
            )
        )
