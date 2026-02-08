"""
===============================================================================
USE CASE: Grant ACL Entry
===============================================================================

Otorga acceso a un usuario en un workspace con un rol específico (VIEWER/EDITOR).
Idempotente: si ya existe, actualiza el rol.

Reglas:
  - Workspace debe existir y no estar archivado.
  - Solo owner o admin pueden gestionar ACL (can_manage_acl).
  - Upsert: grant repetido actualiza rol sin error.
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from ....domain.entities import AclEntry, AclRole
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_manage_acl
from .workspace_results import WorkspaceError, WorkspaceErrorCode


class AclEntryResult:
    """Resultado de operación sobre una entrada ACL."""

    __slots__ = ("entry", "error")

    def __init__(
        self,
        entry: AclEntry | None = None,
        error: WorkspaceError | None = None,
    ) -> None:
        self.entry = entry
        self.error = error


class GrantAclUseCase:
    """Otorga acceso a un usuario en un workspace."""

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
        user_id: UUID,
        role: AclRole = AclRole.VIEWER,
    ) -> AclEntryResult:
        """
        Otorga acceso.

        Pasos:
          1. Validar workspace (existe, no archivado).
          2. Autorizar actor (can_manage_acl).
          3. Upsert en ACL repo.
        """
        # 1. Cargar workspace
        workspace = self._workspaces.get_workspace(workspace_id)
        if workspace is None or workspace.is_archived:
            return AclEntryResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        # 2. Autorización
        if not can_manage_acl(workspace, actor):
            return AclEntryResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        # 3. Upsert
        granted_by = actor.user_id if actor else None
        entry = self._acls.grant_access(
            workspace_id, user_id, role, granted_by=granted_by
        )

        return AclEntryResult(entry=entry)
