"""
Name: Workspace Access Policy

Responsibilities:
  - Decide read/write/ACL permissions for workspaces
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from ..users import UserRole
from .entities import Workspace, WorkspaceVisibility


@dataclass(frozen=True)
class WorkspaceActor:
    """R: Actor context for workspace access decisions."""

    user_id: UUID | None
    role: UserRole | None


def _is_owner(workspace: Workspace, actor: WorkspaceActor) -> bool:
    return (
        workspace.owner_user_id is not None
        and actor.user_id == workspace.owner_user_id
    )


def _is_shared_member(
    actor: WorkspaceActor, shared_user_ids: Iterable[UUID] | None
) -> bool:
    if actor.user_id is None or not shared_user_ids:
        return False
    return actor.user_id in set(shared_user_ids)


def can_read_workspace(
    workspace: Workspace,
    actor: WorkspaceActor | None,
    *,
    shared_user_ids: Iterable[UUID] | None = None,
) -> bool:
    """R: Read access policy for workspaces."""
    if actor is None or actor.role is None:
        return False

    if actor.role == UserRole.ADMIN:
        return True

    if _is_owner(workspace, actor):
        return True

    if actor.role != UserRole.EMPLOYEE:
        return False

    if workspace.visibility == WorkspaceVisibility.ORG_READ:
        return True

    if workspace.visibility == WorkspaceVisibility.SHARED:
        return _is_shared_member(actor, shared_user_ids)

    return False


def can_write_workspace(workspace: Workspace, actor: WorkspaceActor | None) -> bool:
    """R: Write access policy for workspaces."""
    if actor is None or actor.role is None:
        return False

    if actor.role == UserRole.ADMIN:
        return True

    return _is_owner(workspace, actor)


def can_manage_acl(workspace: Workspace, actor: WorkspaceActor | None) -> bool:
    """R: ACL management policy for workspaces."""
    return can_write_workspace(workspace, actor)
