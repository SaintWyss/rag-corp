"""
Name: In-Memory Workspace ACL Repository

Responsibilities:
  - Store workspace ACLs in memory
  - Provide basic CRUD for share lists
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
        self._acls: Dict[UUID, List[UUID]] = {}

    def list_workspace_acl(self, workspace_id: UUID) -> List[UUID]:
        with self._lock:
            return list(self._acls.get(workspace_id, []))

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: List[UUID]) -> None:
        unique_ids = list(dict.fromkeys(user_ids))
        with self._lock:
            self._acls[workspace_id] = unique_ids
