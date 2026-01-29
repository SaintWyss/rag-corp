"""
CRC — infrastructure/repositories/in_memory_workspace_repo.py

Name
- InMemoryWorkspaceRepository

Responsibilities
- Store workspaces in memory (tests/local dev).
- Provide basic CRUD and archive semantics (archived_at).
- Provide v6 listing helpers used by use cases:
  - list_workspaces_by_visibility
  - list_workspaces_by_ids

Collaborators
- domain.entities.Workspace, WorkspaceVisibility
- domain.repositories.WorkspaceRepository

Constraints / Notes
- Thread-safe access (Lock).
- Deterministic ordering aligned with Postgres repository:
  - created_at DESC, name ASC
- Repository only: no RBAC/ACL decision logic here.
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

    def _sort_workspaces(self, items: List[Workspace]) -> None:
        """
        R: In-place deterministic ordering aligned with Postgres:
            ORDER BY created_at DESC NULLS LAST, name ASC
        """

        def created_key(w: Workspace) -> datetime:
            # R: Treat None as very old to emulate NULLS LAST in DESC ordering.
            return w.created_at or datetime.min.replace(tzinfo=timezone.utc)

        items.sort(key=lambda w: (-created_key(w).timestamp(), w.name))

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """R: List workspaces, optionally filtered by owner."""
        with self._lock:
            workspaces = list(self._workspaces.values())

        result: List[Workspace] = []
        for workspace in workspaces:
            if owner_user_id is not None and workspace.owner_user_id != owner_user_id:
                continue
            if not include_archived and workspace.archived_at is not None:
                continue
            result.append(workspace)

        self._sort_workspaces(result)
        return result

    def list_workspaces_by_visibility(
        self,
        visibility: WorkspaceVisibility,
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """R: List workspaces filtered by visibility (e.g., ORG_READ)."""
        with self._lock:
            workspaces = list(self._workspaces.values())

        result: List[Workspace] = []
        for workspace in workspaces:
            if workspace.visibility != visibility:
                continue
            if not include_archived and workspace.archived_at is not None:
                continue
            result.append(workspace)

        self._sort_workspaces(result)
        return result

    def list_workspaces_by_ids(
        self,
        workspace_ids: List[UUID],
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        R: List workspaces by explicit set of IDs.

        Contract requirements:
            - Return [] when workspace_ids is empty.
            - Skip missing IDs.
            - Respect include_archived.
        """
        if not workspace_ids:
            return []

        wanted = set(workspace_ids)
        with self._lock:
            workspaces = [w for wid, w in self._workspaces.items() if wid in wanted]

        result: List[Workspace] = []
        for workspace in workspaces:
            if not include_archived and workspace.archived_at is not None:
                continue
            result.append(workspace)

        self._sort_workspaces(result)
        return result

    def list_workspaces_visible_to_user(
        self,
        user_id: UUID,
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        R: List workspaces visible to a user (owned + ORG_READ + SHARED if in shared_user_ids).
        """
        with self._lock:
            workspaces = list(self._workspaces.values())

        result: List[Workspace] = []
        for workspace in workspaces:
            if not include_archived and workspace.archived_at is not None:
                continue
            if workspace.owner_user_id == user_id:
                result.append(workspace)
                continue
            if workspace.visibility == WorkspaceVisibility.ORG_READ:
                result.append(workspace)
                continue
            if (
                workspace.visibility == WorkspaceVisibility.SHARED
                and user_id in set(workspace.shared_user_ids or [])
            ):
                result.append(workspace)

        self._sort_workspaces(result)
        return result

    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        """R: Fetch a workspace by ID."""
        with self._lock:
            return self._workspaces.get(workspace_id)

    def get_workspace_by_owner_and_name(
        self,
        owner_user_id: UUID | None,
        name: str,
    ) -> Optional[Workspace]:
        """R: Fetch a workspace by owner + name (uniqueness check)."""
        normalized = name.strip().lower()
        with self._lock:
            for workspace in self._workspaces.values():
                if workspace.owner_user_id != owner_user_id:
                    continue
                if workspace.name.strip().lower() == normalized:
                    return workspace
        return None

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """R: Persist a new workspace in memory."""
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
        """R: Update workspace attributes in memory."""
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
        """R: Archive (soft-delete) a workspace in memory (sets archived_at)."""
        with self._lock:
            current = self._workspaces.get(workspace_id)
            if not current:
                return False
            if current.archived_at is not None:
                return True

            now = datetime.now(timezone.utc)
            updated = Workspace(
                id=current.id,
                name=current.name,
                visibility=current.visibility,
                owner_user_id=current.owner_user_id,
                description=current.description,
                allowed_roles=list(current.allowed_roles or []),
                created_at=current.created_at,
                updated_at=now,
                archived_at=now,
            )
            self._workspaces[workspace_id] = updated
            return True
