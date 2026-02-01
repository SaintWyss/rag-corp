"""
===============================================================================
TARJETA CRC — domain/workspace_policy.py
===============================================================================

Módulo:
    Política de Acceso a Workspaces (Lectura/Escritura/ACL)

Responsabilidades:
    - Definir reglas puras de acceso a workspaces (sin DB, sin FastAPI).
    - Separar "policy" de "repos" (repos solo traen datos, policy decide).
    - Ser 100% testeable: funciones puras, inputs explícitos.

Colaboradores:
    - domain.entities.Workspace, WorkspaceVisibility
    - identity.users.UserRole (catálogo de roles)
    - application: resolve_workspace_for_read/write usa esta policy.

Reglas (intención):
    - Admin puede todo.
    - Owner puede leer/escribir/gestionar ACL.
    - Employee puede leer ORG_READ.
    - SHARED requiere pertenecer al ACL (shared_user_ids).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from ..identity.users import UserRole
from .entities import Workspace, WorkspaceVisibility


@dataclass(frozen=True, slots=True)
class WorkspaceActor:
    """Actor para decisiones de acceso a workspace."""

    user_id: UUID | None
    role: UserRole | None


def _is_owner(workspace: Workspace, actor: WorkspaceActor) -> bool:
    return (
        workspace.owner_user_id is not None and actor.user_id == workspace.owner_user_id
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
    """Evalúa permiso de lectura."""
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
        shared_ids = shared_user_ids or workspace.shared_user_ids
        return _is_shared_member(actor, shared_ids)

    return False


def can_write_workspace(workspace: Workspace, actor: WorkspaceActor | None) -> bool:
    """Evalúa permiso de escritura."""
    if actor is None or actor.role is None:
        return False

    if actor.role == UserRole.ADMIN:
        return True

    return _is_owner(workspace, actor)


def can_manage_acl(workspace: Workspace, actor: WorkspaceActor | None) -> bool:
    """Evalúa permiso para gestionar ACL."""
    return can_write_workspace(workspace, actor)
