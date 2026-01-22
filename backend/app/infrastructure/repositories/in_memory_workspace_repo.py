"""
Name: In-Memory Workspace Repository

Responsibilities:
  - Store workspaces in memory
  - Provide basic CRUD and archive semantics
  - Enforce thread-safe access
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID

from ...domain.entities import Workspace, WorkspaceVisibility
from ...domain.repositories import WorkspaceRepository


class InMemoryWorkspaceRepository(WorkspaceRepository):
    """R: Thread-safe in-memory workspace repository."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._workspaces: Dict[UUID, Workspace] = {}

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> List[Workspace]:
        with self._lock:
            workspaces = list(self._workspaces.values())

        result: List[Workspace] = []
        for workspace in workspaces:
            if owner_user_id is not None and workspace.owner_user_id != owner_user_id:
                continue
            if not include_archived and workspace.archived_at is not None:
                continue
            result.append(workspace)

        result.sort(key=lambda item: (item.created_at or datetime.min, item.name))
        return result

    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def get_workspace_by_owner_and_name(
        self, owner_user_id: UUID | None, name: str
    ) -> Optional[Workspace]:
        normalized = name.strip().lower()
        with self._lock:
            for workspace in self._workspaces.values():
                if workspace.owner_user_id != owner_user_id:
                    continue
                if workspace.name.strip().lower() == normalized:
                    return workspace
        return None

    def create_workspace(self, workspace: Workspace) -> Workspace:
        now = datetime.now(timezone.utc)
        created = Workspace(
            id=workspace.id,
            name=workspace.name,
            visibility=workspace.visibility,
            owner_user_id=workspace.owner_user_id,
            description=workspace.description,
            allowed_roles=list(workspace.allowed_roles or []),
            created_at=now,
            updated_at=now,
            archived_at=workspace.archived_at,
        )
        with self._lock:
            self._workspaces[workspace.id] = created
        return created

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: WorkspaceVisibility | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Optional[Workspace]:
        with self._lock:
            current = self._workspaces.get(workspace_id)
            if not current:
                return None
            updated = Workspace(
                id=current.id,
                name=name if name is not None else current.name,
                visibility=visibility if visibility is not None else current.visibility,
                owner_user_id=current.owner_user_id,
                description=(
                    description if description is not None else current.description
                ),
                allowed_roles=(
                    list(allowed_roles)
                    if allowed_roles is not None
                    else list(current.allowed_roles or [])
                ),
                created_at=current.created_at,
                updated_at=datetime.now(timezone.utc),
                archived_at=current.archived_at,
            )
            self._workspaces[workspace_id] = updated
            return updated

    def archive_workspace(self, workspace_id: UUID) -> bool:
        with self._lock:
            current = self._workspaces.get(workspace_id)
            if not current:
                return False
            if current.archived_at is not None:
                return True
            updated = Workspace(
                id=current.id,
                name=current.name,
                visibility=current.visibility,
                owner_user_id=current.owner_user_id,
                description=current.description,
                allowed_roles=list(current.allowed_roles or []),
                created_at=current.created_at,
                updated_at=datetime.now(timezone.utc),
                archived_at=datetime.now(timezone.utc),
            )
            self._workspaces[workspace_id] = updated
            return True
