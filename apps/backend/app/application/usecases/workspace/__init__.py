"""
===============================================================================
WORKSPACE USE CASES PACKAGE (Public API / Exports)
===============================================================================

Name:
    Workspace Use Cases (package exports)

Business Goal:
    Exponer un punto único, estable y explícito de importación para los casos
    de uso de Workspaces, sus DTOs y helpers asociados.

Why (Context / Intención):
    - Evita imports “dispersos” desde módulos internos.
    - Define una API pública clara para la capa application:
        * qué casos de uso existen
        * qué DTOs/resultados se exponen
        * qué helpers están autorizados a ser consumidos por otras features
    - Facilita refactors:
        * mover archivos internos no rompe a consumidores si este módulo mantiene
          la misma interfaz pública.

-------------------------------------------------------------------------------
CRC CARD (Module-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Component:
    workspace usecases package (__init__.py)

Responsibilities:
    - Re-exportar casos de uso principales del subdominio Workspace.
    - Re-exportar DTOs/resultados y errores compartidos.
    - Re-exportar helpers de acceso a workspace (read/write resolution).
    - Definir __all__ como contrato de API pública del paquete.

Collaborators:
    - Módulos internos del paquete:
        archive_workspace, create_workspace, get_workspace, list_workspaces,
        publish_workspace, share_workspace, update_workspace, workspace_access,
        workspace_results
===============================================================================
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Use Cases
# -----------------------------------------------------------------------------
from .archive_workspace import ArchiveWorkspaceUseCase
from .create_workspace import CreateWorkspaceInput, CreateWorkspaceUseCase
from .get_workspace import GetWorkspaceUseCase
from .grant_acl import AclEntryResult, GrantAclUseCase
from .list_acl import AclListResult, ListAclUseCase
from .list_workspaces import ListWorkspacesUseCase
from .publish_workspace import PublishWorkspaceUseCase
from .revoke_acl import AclRevokeResult, RevokeAclUseCase
from .share_workspace import ShareWorkspaceUseCase
from .update_workspace import UpdateWorkspaceUseCase

# -----------------------------------------------------------------------------
# Helpers (shared logic for document/RAG use cases)
# -----------------------------------------------------------------------------
from .workspace_access import resolve_workspace_for_read, resolve_workspace_for_write

# -----------------------------------------------------------------------------
# DTOs / Result models
# -----------------------------------------------------------------------------
from .workspace_results import (
    ArchiveWorkspaceResult,
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceListResult,
    WorkspaceResult,
)

# -----------------------------------------------------------------------------
# Public API (explicit exports)
# -----------------------------------------------------------------------------
__all__ = [
    # Use Cases
    "CreateWorkspaceInput",
    "CreateWorkspaceUseCase",
    "GetWorkspaceUseCase",
    "ListWorkspacesUseCase",
    "UpdateWorkspaceUseCase",
    "ArchiveWorkspaceUseCase",
    "PublishWorkspaceUseCase",
    "ShareWorkspaceUseCase",
    "GrantAclUseCase",
    "RevokeAclUseCase",
    "ListAclUseCase",
    # Helpers
    "resolve_workspace_for_read",
    "resolve_workspace_for_write",
    # DTOs / Result models
    "WorkspaceResult",
    "WorkspaceListResult",
    "ArchiveWorkspaceResult",
    "AclEntryResult",
    "AclListResult",
    "AclRevokeResult",
    "WorkspaceError",
    "WorkspaceErrorCode",
]
