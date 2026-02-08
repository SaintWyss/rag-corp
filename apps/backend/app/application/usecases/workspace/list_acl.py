"""
===============================================================================
USE CASE: List ACL Entries
===============================================================================

Lista las entradas de ACL (usuario + rol) de un workspace.

Reglas:
  - Workspace debe existir y no estar archivado.
  - Solo owner o admin pueden ver el ACL (can_manage_acl).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from ....domain.entities import AclEntry
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_manage_acl
from .workspace_results import WorkspaceError, WorkspaceErrorCode


@dataclass
class AclListResult:
    """Resultado de listado de ACL."""

    entries: list[AclEntry] = field(default_factory=list)
    error: WorkspaceError | None = None


class ListAclUseCase:
    """Lista entradas ACL de un workspace."""

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
    ) -> AclListResult:
        """
        Lista ACL.

        Pasos:
          1. Validar workspace (existe, no archivado).
          2. Autorizar actor (can_manage_acl).
          3. Retornar entradas.
        """
        # 1. Cargar workspace
        workspace = self._workspaces.get_workspace(workspace_id)
        if workspace is None or workspace.is_archived:
            return AclListResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        # 2. Autorización
        if not can_manage_acl(workspace, actor):
            return AclListResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        # 3. Listar
        entries = self._acls.list_acl_entries(workspace_id)
        return AclListResult(entries=entries)
