"""
===============================================================================
USE CASE: Create Workspace
===============================================================================

Name:
    Create Workspace Use Case

Business Goal:
    Crear un nuevo workspace garantizando:
      - unicidad del nombre para el owner
      - asignación correcta de owner
      - visibilidad inicial controlada (siempre PRIVATE)

Why (Context / Intención):
    - Un workspace es el “contenedor” de documentos y chat/RAG.
    - La creación debe ser segura y predecible (invariantes fuertes):
        * nombre válido (no vacío)
        * no duplicado para el mismo owner
        * visibilidad inicial inmutable a PRIVATE (evita exposición accidental)
        * creación restringida (provisionamiento controlado)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    CreateWorkspaceUseCase

Responsibilities:
    - Validar actor (existencia, identidad y rol).
    - Normalizar el nombre del workspace.
    - Validar invariantes de creación (visibilidad inicial = PRIVATE).
    - Resolver owner efectivo (por defecto actor, con override admin).
    - Verificar unicidad (owner + name).
    - Construir entidad Workspace y persistirla en repositorio.
    - Devolver un resultado tipado (WorkspaceResult) con error estable.

Collaborators:
    - WorkspaceRepository:
        get_workspace_by_owner_and_name(owner_id, name)
        create_workspace(workspace) -> Workspace
    - WorkspaceActor:
        user_id, role
    - Domain entities:
        Workspace, WorkspaceVisibility
    - Identity:
        UserRole (para reglas de autorización)
    - workspace_results:
        WorkspaceResult / WorkspaceError / WorkspaceErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - CreateWorkspaceInput:
        name: str
        description: Optional[str]
        actor: Optional[WorkspaceActor]
        visibility: Optional[WorkspaceVisibility]   (solo se acepta PRIVATE o None)
        owner_user_id: Optional[UUID]              (override admin)

Outputs:
    - WorkspaceResult:
        - workspace: Workspace | None
        - error: WorkspaceError | None

Error Mapping:
    - FORBIDDEN:
        - actor ausente/inválido
        - actor no autorizado (rol incorrecto)
    - VALIDATION_ERROR:
        - name vacío / inválido
        - visibility diferente a PRIVATE
    - CONFLICT:
        - ya existe workspace con mismo nombre para el mismo owner
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from ....domain.entities import Workspace, WorkspaceVisibility
from ....domain.repositories import WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor
from ....identity.users import UserRole
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


@dataclass(frozen=True)
class CreateWorkspaceInput:
    """
    DTO de entrada del caso de uso.

    Notas:
      - actor: representa al usuario que ejecuta la acción (autenticación/autorización).
      - visibility: se permite pasarlo, pero en creación SOLO se acepta PRIVATE o None.
      - owner_user_id: override de ownership (solo aplica si actor es admin; acá
        se valida porque el provisioning está restringido).
    """

    name: str
    description: str | None = None
    actor: WorkspaceActor | None = None
    visibility: WorkspaceVisibility | None = None
    owner_user_id: UUID | None = (
        None  # Override permitido para provisioning controlado.
    )


class CreateWorkspaceUseCase:
    """
    Use Case (Application Service / Command):
        Orquesta la creación de un workspace aplicando reglas de negocio y
        delegando persistencia al repositorio.
    """

    def __init__(self, repository: WorkspaceRepository) -> None:
        # Naming explícito: evita ambigüedad y mejora legibilidad.
        self._workspaces = repository

    def execute(self, input_data: CreateWorkspaceInput) -> WorkspaceResult:
        """
        Crea un workspace nuevo.

        Precondiciones:
          - input_data.actor debe existir y tener user_id y role.
          - input_data.name debe ser no vacío luego de normalizar.

        Poscondiciones (si SUCCESS):
          - Se persiste un Workspace con:
              * id nuevo
              * name normalizado
              * visibility = PRIVATE
              * owner_user_id = owner efectivo
        """

        # ---------------------------------------------------------------------
        # 1) Validar actor (autorización base + rol).
        # ---------------------------------------------------------------------
        actor = input_data.actor
        if actor is None or actor.user_id is None or actor.role is None:
            # Se trata como FORBIDDEN porque no hay identidad/rol para evaluar permisos.
            return self._forbidden("Actor is required to create workspace.")

        # Regla de autorización: creación restringida.
        # Si mañana cambia (ej: permitir self-service), este bloque es el punto único.
        if actor.role != UserRole.ADMIN:
            return self._forbidden("Only admins can create workspaces.")

        # ---------------------------------------------------------------------
        # 2) Normalizar y validar nombre (invariante).
        # ---------------------------------------------------------------------
        normalized_name = self._normalize_name(input_data.name)
        if not normalized_name:
            return self._validation_error("Workspace name is required.")

        # ---------------------------------------------------------------------
        # 3) Validar visibilidad inicial (invariante).
        # ---------------------------------------------------------------------
        # En creación siempre queda PRIVATE para evitar exposición accidental.
        if (
            input_data.visibility is not None
            and input_data.visibility != WorkspaceVisibility.PRIVATE
        ):
            return self._validation_error(
                "Workspace visibility must be PRIVATE on creation."
            )

        # ---------------------------------------------------------------------
        # 4) Resolver owner efectivo.
        # ---------------------------------------------------------------------
        # Admin puede provisionar el workspace para otro usuario, si owner_user_id viene.
        effective_owner_id = input_data.owner_user_id or actor.user_id

        # ---------------------------------------------------------------------
        # 5) Verificar unicidad (owner + name).
        # ---------------------------------------------------------------------
        # Previene duplicados dentro del mismo "espacio" del owner.
        existing = self._workspaces.get_workspace_by_owner_and_name(
            effective_owner_id,
            normalized_name,
        )
        if existing is not None:
            return self._conflict("Workspace name already exists for owner.")

        # ---------------------------------------------------------------------
        # 6) Construir entidad y persistirla.
        # ---------------------------------------------------------------------
        # La entidad se crea con invariantes firmes (visibility forzada a PRIVATE).
        workspace = Workspace(
            id=uuid4(),
            name=normalized_name,
            description=input_data.description,
            visibility=WorkspaceVisibility.PRIVATE,
            owner_user_id=effective_owner_id,
        )

        created = self._workspaces.create_workspace(workspace)

        # ---------------------------------------------------------------------
        # 7) Devolver resultado tipado.
        # ---------------------------------------------------------------------
        return WorkspaceResult(workspace=created)

    # =========================================================================
    # Helpers privados: evitan duplicación y hacen execute() más “escaneable”.
    # =========================================================================

    @staticmethod
    def _normalize_name(raw_name: str) -> str:
        """
        Normaliza el nombre para consistencia y validación.

        - strip(): evita nombres con espacios “fantasma”
        - (Opcional futuro) colapsar espacios internos, limitar longitud, etc.
        """
        return (raw_name or "").strip()

    @staticmethod
    def _forbidden(message: str) -> WorkspaceResult:
        """Crea un WorkspaceResult consistente para FORBIDDEN."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.FORBIDDEN,
                message=message,
            )
        )

    @staticmethod
    def _validation_error(message: str) -> WorkspaceResult:
        """Crea un WorkspaceResult consistente para VALIDATION_ERROR."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.VALIDATION_ERROR,
                message=message,
            )
        )

    @staticmethod
    def _conflict(message: str) -> WorkspaceResult:
        """Crea un WorkspaceResult consistente para CONFLICT."""
        return WorkspaceResult(
            error=WorkspaceError(
                code=WorkspaceErrorCode.CONFLICT,
                message=message,
            )
        )
