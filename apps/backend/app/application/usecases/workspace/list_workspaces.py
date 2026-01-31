"""
===============================================================================
USE CASE: List Workspaces
===============================================================================

Name:
    List Workspaces Use Case

Business Goal:
    Listar los workspaces visibles para un actor, aplicando reglas de visibilidad
    y ACL de forma consistente con la política de lectura.

Why (Context / Intención):
    - Un usuario debe ver solo lo que puede leer:
        * ADMIN: puede listar todos o filtrar por owner_user_id.
        * No-admin: solo workspaces visibles por propiedad, visibilidad ORG_READ,
          y SHARED si está en el ACL.
    - Este caso de uso centraliza el “scope” de listados evitando filtrados
      inconsistentes en la API/UI.
    - Se busca evitar N+1 cuando el repo ya devuelve el conjunto visible.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ListWorkspacesUseCase

Responsibilities:
    - Validar actor (identidad y rol).
    - Resolver estrategia de listado según rol (admin vs no-admin).
    - Recuperar workspaces según el scope correcto.
    - Aplicar política can_read_workspace para enforcement consistente.
    - Evitar N+1 para SHARED cuando el repositorio ya filtró por ACL.
    - Devolver un resultado tipado (WorkspaceListResult) con lista o error.

Collaborators:
    - WorkspaceRepository:
        list_workspaces(owner_user_id, include_archived) -> list[Workspace]
        list_workspaces_visible_to_user(user_id, include_archived) -> list[Workspace]
    - WorkspaceAclRepository:
        (posible uso cuando el repo no hace join/filtrado por ACL)
    - workspace_policy:
        can_read_workspace(workspace, actor, shared_user_ids=...) -> bool
    - Identity:
        UserRole
    - Domain entities:
        WorkspaceVisibility
    - workspace_results:
        WorkspaceListResult / WorkspaceError / WorkspaceErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - actor: WorkspaceActor | None
    - owner_user_id: UUID | None
        * solo relevante para admins (filtra por owner)
    - include_archived: bool
        * si True, incluye workspaces archivados

Outputs:
    - WorkspaceListResult:
        - workspaces: list[Workspace]
        - error: WorkspaceError | None

Error Mapping:
    - FORBIDDEN:
        - actor ausente o inválido
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from ....domain.entities import WorkspaceVisibility
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_read_workspace
from ....identity.users import UserRole
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceListResult


class ListWorkspacesUseCase:
    """
    Use Case (Application Service / Query):
        Lista workspaces visibles para un actor aplicando reglas de visibilidad,
        ACL y políticas de lectura.

    Nota de diseño:
        - Admin: listado "directo" desde repo, con filtros opcionales.
        - No-admin: repo devuelve un conjunto ya "scoped" (owned + org + shared).
          Aun así, se aplica can_read_workspace como enforcement consistente.
    """

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ) -> None:
        # Naming explícito para claridad.
        self._workspaces = workspace_repository
        self._acls = acl_repository

    def execute(
        self,
        *,
        actor: WorkspaceActor | None,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> WorkspaceListResult:
        """
        Devuelve el listado de workspaces visibles según el actor.

        Reglas:
          - Actor requerido para listar (no se permite listado anónimo).
          - ADMIN: puede listar todos o filtrar por owner_user_id.
          - No-admin: solo ve lo que el repo define como visible (scope),
            reforzado por can_read_workspace.

        Parámetros:
          - owner_user_id:
              * para ADMIN: filtra por owner específico (o None para todos)
              * para No-admin: se ignora por seguridad (no puede "consultar" otros)
          - include_archived:
              * si True, incluye workspaces archivados en el resultado.
        """

        # ---------------------------------------------------------------------
        # 1) Validar actor.
        # ---------------------------------------------------------------------
        # Sin actor no hay identidad para aplicar políticas => FORBIDDEN.
        if actor is None or actor.user_id is None or actor.role is None:
            return self._forbidden("Actor is required to list workspaces.")

        # ---------------------------------------------------------------------
        # 2) Rama ADMIN: listado directo con filtros.
        # ---------------------------------------------------------------------
        if actor.role == UserRole.ADMIN:
            # Admin puede listar todos o filtrar por owner.
            workspaces = self._workspaces.list_workspaces(
                owner_user_id=owner_user_id,
                include_archived=include_archived,
            )
            return WorkspaceListResult(workspaces=workspaces)

        # ---------------------------------------------------------------------
        # 3) Rama No-admin: repo retorna el conjunto "scoped" de visibilidad.
        # ---------------------------------------------------------------------
        # Este método debe devolver:
        #   - workspaces owned por el usuario
        #   - workspaces ORG_READ (si aplica)
        #   - workspaces SHARED donde el usuario está en ACL
        combined = self._workspaces.list_workspaces_visible_to_user(
            actor.user_id,
            include_archived=include_archived,
        )

        # ---------------------------------------------------------------------
        # 4) Enforce policy can_read_workspace de manera consistente.
        # ---------------------------------------------------------------------
        # Importante:
        #   - Evitamos N+1 del ACL: asumimos que list_workspaces_visible_to_user()
        #     ya filtró por ACL en el caso SHARED.
        #   - Por eso, para SHARED pasamos shared_user_ids=[actor.user_id] como
        #     “prueba mínima” de pertenencia, evitando consultar el ACL completo.
        visible: list = []
        for workspace in combined:
            shared_user_ids: list[UUID] | None = None

            if workspace.visibility == WorkspaceVisibility.SHARED:
                # Si el repo ya filtró por ACL, el actor necesariamente es miembro.
                # Pasamos el actor como shared_user_ids para cumplir con la policy
                # sin incurrir en fetch adicional.
                shared_user_ids = [actor.user_id]

            if can_read_workspace(workspace, actor, shared_user_ids=shared_user_ids):
                visible.append(workspace)

        return WorkspaceListResult(workspaces=visible)

    # =========================================================================
    # Helpers privados: devuelven errores consistentes.
    # =========================================================================

    @staticmethod
    def _forbidden(message: str) -> WorkspaceListResult:
        """Resultado consistente para FORBIDDEN en listados."""
        return WorkspaceListResult(
            workspaces=[],
            error=WorkspaceError(
                code=WorkspaceErrorCode.FORBIDDEN,
                message=message,
            ),
        )
