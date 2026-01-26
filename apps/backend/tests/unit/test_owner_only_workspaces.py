"""
Name: Owner-Only Workspace Tests (ADR-008)

Responsibilities:
  - Validate that employees only see/create workspaces they own
  - Validate that admins can see all and optionally assign owners
  - Cover list, get, and create use cases
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from app.application.usecases.create_workspace import (
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
)
from app.application.usecases.get_workspace import GetWorkspaceUseCase
from app.application.usecases.list_workspaces import ListWorkspacesUseCase
from app.application.usecases.workspace_results import WorkspaceErrorCode
from app.domain.entities import Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

pytestmark = pytest.mark.unit


class FakeWorkspaceRepository:
    """Minimal fake for testing owner-only behavior."""

    def __init__(self, workspaces: list[Workspace] | None = None):
        self._workspaces: dict[UUID, Workspace] = {
            ws.id: ws for ws in (workspaces or [])
        }

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[Workspace]:
        result = list(self._workspaces.values())
        if owner_user_id is not None:
            result = [ws for ws in result if ws.owner_user_id == owner_user_id]
        if not include_archived:
            result = [ws for ws in result if ws.archived_at is None]
        return result

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    def get_workspace_by_owner_and_name(
        self, owner_user_id: UUID | None, name: str
    ) -> Workspace | None:
        normalized = name.strip().lower()
        for workspace in self._workspaces.values():
            if workspace.owner_user_id != owner_user_id:
                continue
            if workspace.name.strip().lower() == normalized:
                return workspace
        return None

    def create_workspace(self, workspace: Workspace) -> Workspace:
        self._workspaces[workspace.id] = workspace
        return workspace


class FakeWorkspaceAclRepository:
    """Minimal fake for ACL lookups."""

    def __init__(self, acl: dict[UUID, list[UUID]] | None = None):
        self._acl = acl or {}

    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        return list(self._acl.get(workspace_id, []))


def _actor(user_id: UUID, role: UserRole) -> WorkspaceActor:
    return WorkspaceActor(user_id=user_id, role=role)


def _workspace(
    *,
    name: str,
    owner_user_id: UUID,
    visibility: WorkspaceVisibility = WorkspaceVisibility.PRIVATE,
) -> Workspace:
    return Workspace(
        id=uuid4(),
        name=name,
        visibility=visibility,
        owner_user_id=owner_user_id,
    )


# =============================================================================
# LIST WORKSPACES - OWNER-ONLY FOR EMPLOYEES
# =============================================================================


class TestListWorkspacesOwnerOnly:
    """ADR-008: Employee sees only owned workspaces at DB level."""

    def test_employee_only_sees_own_workspaces(self):
        """Employee cannot see workspaces owned by others."""
        employee_id = uuid4()
        other_owner = uuid4()

        ws_own = _workspace(name="My Workspace", owner_user_id=employee_id)
        ws_other = _workspace(name="Other Workspace", owner_user_id=other_owner)

        repo = FakeWorkspaceRepository([ws_own, ws_other])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(actor=_actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is None
        assert len(result.workspaces) == 1
        assert result.workspaces[0].id == ws_own.id

    def test_employee_cannot_bypass_owner_filter(self):
        """Employee passing owner_user_id of another user gets empty list."""
        employee_id = uuid4()
        other_owner = uuid4()

        ws_other = _workspace(name="Other Workspace", owner_user_id=other_owner)

        repo = FakeWorkspaceRepository([ws_other])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        # Even if employee tries to pass owner_user_id=other_owner, they get nothing
        result = use_case.execute(
            actor=_actor(employee_id, UserRole.EMPLOYEE),
            owner_user_id=other_owner,  # This should be ignored for employees
        )

        assert result.error is None
        assert len(result.workspaces) == 0  # Cannot see other's workspaces

    def test_admin_sees_all_workspaces(self):
        """Admin can see all workspaces regardless of owner."""
        admin_id = uuid4()
        owner_a = uuid4()
        owner_b = uuid4()

        ws_a = _workspace(name="Owner A Workspace", owner_user_id=owner_a)
        ws_b = _workspace(name="Owner B Workspace", owner_user_id=owner_b)

        repo = FakeWorkspaceRepository([ws_a, ws_b])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(actor=_actor(admin_id, UserRole.ADMIN))

        assert result.error is None
        assert len(result.workspaces) == 2
        assert {ws.id for ws in result.workspaces} == {ws_a.id, ws_b.id}

    def test_admin_can_filter_by_specific_owner(self):
        """Admin can optionally filter by a specific owner."""
        admin_id = uuid4()
        owner_a = uuid4()
        owner_b = uuid4()

        ws_a = _workspace(name="Owner A Workspace", owner_user_id=owner_a)
        ws_b = _workspace(name="Owner B Workspace", owner_user_id=owner_b)

        repo = FakeWorkspaceRepository([ws_a, ws_b])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(
            actor=_actor(admin_id, UserRole.ADMIN),
            owner_user_id=owner_a,
        )

        assert result.error is None
        assert len(result.workspaces) == 1
        assert result.workspaces[0].id == ws_a.id


# =============================================================================
# GET WORKSPACE - POLICY ENFORCEMENT
# =============================================================================


class TestGetWorkspaceOwnerOnly:
    """ADR-008: Employee cannot get workspace they don't own (unless shared)."""

    def test_employee_can_get_own_workspace(self):
        """Employee can get their own private workspace."""
        employee_id = uuid4()
        ws = _workspace(
            name="My Workspace",
            owner_user_id=employee_id,
            visibility=WorkspaceVisibility.PRIVATE,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.id == ws.id

    def test_employee_cannot_get_foreign_private_workspace(self):
        """Employee cannot get private workspace owned by another user."""
        employee_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Other Workspace",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.PRIVATE,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.FORBIDDEN

    def test_admin_can_get_any_workspace(self):
        """Admin can get any workspace regardless of owner."""
        admin_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Other Workspace",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.PRIVATE,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(admin_id, UserRole.ADMIN))

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.id == ws.id


# =============================================================================
# CREATE WORKSPACE - OWNER OVERRIDE ENFORCEMENT
# =============================================================================


class TestCreateWorkspaceOwnerOnly:
    """ADR-008: Employee cannot assign workspace to another user."""

    def test_employee_creates_workspace_as_self(self):
        """Employee creates workspace with self as owner."""
        employee_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="My Workspace",
                actor=_actor(employee_id, UserRole.EMPLOYEE),
            )
        )

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.owner_user_id == employee_id

    def test_employee_cannot_assign_owner_to_another_user(self):
        """Employee passing owner_user_id is ignored - still assigned to self."""
        employee_id = uuid4()
        target_owner = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Sneaky Workspace",
                actor=_actor(employee_id, UserRole.EMPLOYEE),
                owner_user_id=target_owner,  # Should be IGNORED
            )
        )

        assert result.error is None
        assert result.workspace is not None
        # Owner is employee, NOT target_owner
        assert result.workspace.owner_user_id == employee_id
        assert result.workspace.owner_user_id != target_owner

    def test_admin_can_assign_owner_to_another_user(self):
        """Admin can create workspace and assign to another user."""
        admin_id = uuid4()
        target_owner = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Assigned Workspace",
                actor=_actor(admin_id, UserRole.ADMIN),
                owner_user_id=target_owner,
            )
        )

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.owner_user_id == target_owner

    def test_admin_defaults_to_self_if_no_owner_specified(self):
        """Admin without owner_user_id creates workspace as self."""
        admin_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Admin Workspace",
                actor=_actor(admin_id, UserRole.ADMIN),
                # No owner_user_id specified
            )
        )

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.owner_user_id == admin_id
