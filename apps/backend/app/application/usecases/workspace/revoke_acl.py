"""
===============================================================================
USE CASE: Revoke ACL Entry
===============================================================================

Revoca el acceso de un usuario a un workspace.

Reglas:
  - Workspace debe existir y no estar archivado.
  - Solo owner o admin pueden gestionar ACL (can_manage_acl).
  - Si el usuario no tenía acceso, retorna NOT_FOUND (no silencioso).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_manage_acl
from .workspace_results import WorkspaceError, WorkspaceErrorCode


@dataclass
class AclRevokeResult:
    """Resultado de revocación de acceso."""

    revoked: bool = False
    error: WorkspaceError | None = None


class RevokeAclUseCase:
    """Revoca acceso de un usuario a un workspace."""

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
    ) -> AclRevokeResult:
        """
        Revoca acceso.

        Pasos:
          1. Validar workspace (existe, no archivado).
          2. Autorizar actor (can_manage_acl).
          3. Revocar en ACL repo.
          4. Si no existía → NOT_FOUND.
        """
        # 1. Cargar workspace
        workspace = self._workspaces.get_workspace(workspace_id)
        if workspace is None or workspace.is_archived:
            return AclRevokeResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        # 2. Autorización
        if not can_manage_acl(workspace, actor):
            return AclRevokeResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        # 3. Revocar
        existed = self._acls.revoke_access(workspace_id, user_id)

        if not existed:
            return AclRevokeResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="ACL entry not found.",
                )
            )

        return AclRevokeResult(revoked=True)
