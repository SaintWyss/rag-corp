"""
===============================================================================
WORKSPACE ACCESS HELPERS (Read / Write Resolution)
===============================================================================

Name:
    Workspace Access Helpers

Business Goal:
    Centralizar la resolución de acceso a un workspace para casos de uso de
    documentos y RAG (chat), garantizando:
      - verificación uniforme de existencia y estado (no archivado)
      - aplicación consistente de políticas de lectura/escritura
      - construcción estandarizada de errores (DocumentError) para capas que
        operan sobre documentos/chunks

Why (Context / Intención):
    - Los casos de uso de documentos/RAG dependen de un workspace “accesible”.
    - Duplicar checks en múltiples use cases genera inconsistencias y bugs.
    - Centralizar reduce riesgo, facilita mantenimiento y mejora testabilidad.

-------------------------------------------------------------------------------
CRC CARD (Functions-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Component:
    workspace_access helpers (module-level functions)

Responsibilities:
    - Resolver workspace para lectura (read scope), cargando ACL si es SHARED.
    - Resolver workspace para escritura (write scope).
    - Retornar (Workspace | None, DocumentError | None) como contrato estable.
    - Normalizar mensajes/códigos de error en contexto de Document use cases.

Collaborators:
    - WorkspaceRepository:
        get_workspace(workspace_id) -> Workspace | None
    - WorkspaceAclRepository:
        list_workspace_acl(workspace_id) -> list[UUID]
    - workspace_policy:
        can_read_workspace(workspace, actor, shared_user_ids=...) -> bool
        can_write_workspace(workspace, actor) -> bool
    - Domain entities:
        Workspace, WorkspaceVisibility
    - Document results:
        DocumentError, DocumentErrorCode
===============================================================================
"""

from __future__ import annotations

from typing import Final, Tuple
from uuid import UUID

from ....domain.entities import Workspace, WorkspaceVisibility
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import (
    WorkspaceActor,
    can_read_workspace,
    can_write_workspace,
)
from ..documents.document_results import DocumentError, DocumentErrorCode

# -----------------------------------------------------------------------------
# Constants: evitan strings duplicados y garantizan consistencia.
# -----------------------------------------------------------------------------
_RESOURCE_NAME: Final[str] = "Workspace"
_MSG_NOT_FOUND: Final[str] = "Workspace not found."
_MSG_FORBIDDEN: Final[str] = "Access denied."


def resolve_workspace_for_read(
    *,
    workspace_id: UUID,
    actor: WorkspaceActor | None,
    workspace_repository: WorkspaceRepository,
    acl_repository: WorkspaceAclRepository,
) -> Tuple[Workspace | None, DocumentError | None]:
    """
    Resuelve un workspace para operaciones de lectura (Document/RAG).

    Reglas:
      - El workspace debe existir y no estar archivado.
      - Si el workspace es SHARED, se consulta el ACL para validar membresía.
      - Se aplica can_read_workspace como política central de lectura.

    Retorna:
      - (workspace, None) si hay acceso
      - (None, DocumentError) si no existe / archivado / forbidden
    """

    # -------------------------------------------------------------------------
    # 1) Cargar workspace y validar estado.
    # -------------------------------------------------------------------------
    workspace = workspace_repository.get_workspace(workspace_id)
    if workspace is None or workspace.is_archived:
        return None, _not_found_error()

    # -------------------------------------------------------------------------
    # 2) Resolver ACL solo si la política lo necesita (visibilidad SHARED).
    # -------------------------------------------------------------------------
    # Para SHARED, la policy requiere los shared_user_ids para evaluar acceso.
    shared_user_ids: list[UUID] | None = None
    if workspace.visibility == WorkspaceVisibility.SHARED:
        shared_user_ids = acl_repository.list_workspace_acl(workspace_id)

    # -------------------------------------------------------------------------
    # 3) Aplicar política de lectura.
    # -------------------------------------------------------------------------
    if not can_read_workspace(workspace, actor, shared_user_ids=shared_user_ids):
        return None, _forbidden_error()

    return workspace, None


def resolve_workspace_for_write(
    *,
    workspace_id: UUID,
    actor: WorkspaceActor | None,
    workspace_repository: WorkspaceRepository,
) -> Tuple[Workspace | None, DocumentError | None]:
    """
    Resuelve un workspace para operaciones de escritura (Document/RAG).

    Reglas:
      - El workspace debe existir y no estar archivado.
      - Se aplica can_write_workspace como política central de escritura.

    Retorna:
      - (workspace, None) si hay acceso de escritura
      - (None, DocumentError) si no existe / archivado / forbidden
    """

    # -------------------------------------------------------------------------
    # 1) Cargar workspace y validar estado.
    # -------------------------------------------------------------------------
    workspace = workspace_repository.get_workspace(workspace_id)
    if workspace is None or workspace.is_archived:
        return None, _not_found_error()

    # -------------------------------------------------------------------------
    # 2) Aplicar política de escritura.
    # -------------------------------------------------------------------------
    if not can_write_workspace(workspace, actor):
        return None, _forbidden_error()

    return workspace, None


# =============================================================================
# Private helpers: construcción consistente de errores.
# =============================================================================


def _not_found_error() -> DocumentError:
    """
    DocumentError NOT_FOUND consistente cuando el workspace:
      - no existe
      - o está archivado (no se considera “activo” para Document/RAG)
    """
    return DocumentError(
        code=DocumentErrorCode.NOT_FOUND,
        message=_MSG_NOT_FOUND,
        resource=_RESOURCE_NAME,
    )


def _forbidden_error() -> DocumentError:
    """
    DocumentError FORBIDDEN consistente cuando el actor no tiene acceso
    requerido al workspace.
    """
    return DocumentError(
        code=DocumentErrorCode.FORBIDDEN,
        message=_MSG_FORBIDDEN,
        resource=_RESOURCE_NAME,
    )
