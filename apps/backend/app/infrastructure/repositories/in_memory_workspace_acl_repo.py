"""
CRC — infrastructure/repositories/in_memory_workspace_acl_repo.py

Name
- InMemoryWorkspaceAclRepository

Responsibilities
- Store workspace ACLs in memory (for tests/local dev).
- Provide CRUD-like operations for SHARED workspace access lists.
- Provide reverse lookup (v6): list workspace IDs shared to a given user.

Collaborators
- domain.repositories.WorkspaceAclRepository

Constraints / Notes
- Thread-safe access (Lock).
- Deterministic ordering for stable unit tests.
- No business policy here; only stores and returns data.
"""

from __future__ import annotations

from threading import Lock
from typing import Dict, List
from uuid import UUID

from ...domain.repositories import WorkspaceAclRepository


class InMemoryWorkspaceAclRepository(WorkspaceAclRepository):
    """R: Thread-safe in-memory workspace ACL repository."""

    def __init__(self) -> None:
        self._lock = Lock()
        # workspace_id -> [user_id, user_id, ...]
        self._acls: Dict[UUID, List[UUID]] = {}

    def list_workspace_acl(self, workspace_id: UUID) -> List[UUID]:
        """R: Return the user IDs that can read the given workspace."""
        with self._lock:
            return list(self._acls.get(workspace_id, []))

    def list_workspaces_for_user(self, user_id: UUID) -> List[UUID]:
        """
        R: Reverse lookup: return workspace IDs where user_id is present in the ACL.
        """
        with self._lock:
            workspace_ids = [
                ws_id for ws_id, users in self._acls.items() if user_id in users
            ]

        # R: Deterministic ordering helps tests and stable API responses.
        workspace_ids.sort(key=lambda x: str(x))
        return workspace_ids

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: List[UUID]) -> None:
        """R: Replace the ACL entries for a workspace with the provided user IDs."""
        unique_ids = list(dict.fromkeys(user_ids))
        with self._lock:
            self._acls[workspace_id] = unique_ids
