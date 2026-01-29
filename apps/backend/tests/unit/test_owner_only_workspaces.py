"""
CRC — tests/unit/test_owner_only_workspaces.py

Name
- Workspace Listing / Ownership / Visibility Tests (v6)

Responsibilities
- Validate employee visibility rules for listing and getting workspaces:
  - EMPLOYEE can see OWN workspaces
  - EMPLOYEE can see ORG_READ workspaces (global)
  - EMPLOYEE can see SHARED workspaces only if present in ACL
  - EMPLOYEE cannot see PRIVATE workspaces owned by others
- Validate admin behavior:
  - ADMIN can list all workspaces
  - ADMIN can filter list by owner_user_id
- Validate create behavior:
  - EMPLOYEE cannot assign owner_user_id to another user (forced to self)
  - ADMIN can assign owner_user_id (or default to self)

Collaborators
- application.usecases: CreateWorkspaceUseCase, GetWorkspaceUseCase, ListWorkspacesUseCase
- domain.entities: Workspace, WorkspaceVisibility
- domain.workspace_policy: WorkspaceActor
- identity.users: UserRole

Constraints / Notes
- Keep fakes aligned with repository Protocol method signatures used by the use cases
  to avoid runtime AttributeError.
"""

from __future__ import annotations

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
    """Minimal fake repository implementing the methods required by v6 use cases."""

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

    def list_workspaces_by_visibility(
        self,
        visibility: WorkspaceVisibility,
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """Reverse helper used by v6 listing logic (e.g., ORG_READ)."""
        result = [ws for ws in self._workspaces.values() if ws.visibility == visibility]
        if not include_archived:
            result = [ws for ws in result if ws.archived_at is None]
        return result

    def list_workspaces_by_ids(
        self,
        workspace_ids: list[UUID],
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """Helper used by v6 listing logic (SHARED workspaces fetched by ACL IDs)."""
        if not workspace_ids:
            return []
        wanted = set(workspace_ids)
        result = [ws for ws_id, ws in self._workspaces.items() if ws_id in wanted]
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
    """
    Minimal fake ACL repository.

    Stores mapping:
        workspace_id -> [user_id, ...]
    """

    def __init__(self, acl: dict[UUID, list[UUID]] | None = None):
        self._acl = acl or {}

    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        return list(self._acl.get(workspace_id, []))

    def list_workspaces_for_user(self, user_id: UUID) -> list[UUID]:
        """
        Reverse lookup: return workspace IDs where user_id is present.
        v6 listing uses this to find SHARED workspaces.
        """
        workspace_ids = [
            ws_id for ws_id, users in self._acl.items() if user_id in users
        ]
        workspace_ids.sort(key=lambda x: str(x))  # deterministic
        return workspace_ids

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: list[UUID]) -> None:
        unique = list(dict.fromkeys(user_ids))
        self._acl[workspace_id] = unique


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
# LIST WORKSPACES - v6 VISIBILITY RULES
# =============================================================================


class TestListWorkspacesV6:
    """v6: EMPLOYEE sees OWN + ORG_READ + SHARED(if in ACL), but not foreign PRIVATE."""

    def test_employee_sees_own_plus_org_read_plus_shared_member(self):
        employee_id = uuid4()
        other_owner = uuid4()

        ws_own_private = _workspace(
            name="My Private",
            owner_user_id=employee_id,
            visibility=WorkspaceVisibility.PRIVATE,
        )
        ws_other_private = _workspace(
            name="Other Private",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.PRIVATE,
        )
        ws_other_org = _workspace(
            name="Org Visible",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.ORG_READ,
        )
        ws_other_shared = _workspace(
            name="Shared",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.SHARED,
        )

        repo = FakeWorkspaceRepository(
            [ws_own_private, ws_other_private, ws_other_org, ws_other_shared]
        )
        acl_repo = FakeWorkspaceAclRepository({ws_other_shared.id: [employee_id]})
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(actor=_actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is None
        assert {ws.id for ws in result.workspaces} == {
            ws_own_private.id,
            ws_other_org.id,
            ws_other_shared.id,
        }

    def test_employee_passing_owner_user_id_does_not_expand_privileges(self):
        """
        EMPLOYEE cannot use owner_user_id to see someone else's PRIVATE workspaces.
        The parameter is ignored for employees by the v6 use case.
        """
        employee_id = uuid4()
        other_owner = uuid4()

        ws_other_private = _workspace(
            name="Other Private",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.PRIVATE,
        )
        ws_other_org = _workspace(
            name="Org Visible",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.ORG_READ,
        )

        repo = FakeWorkspaceRepository([ws_other_private, ws_other_org])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(
            actor=_actor(employee_id, UserRole.EMPLOYEE),
            owner_user_id=other_owner,
        )

        assert result.error is None
        # Should still see ORG_READ, but not the foreign PRIVATE workspace.
        assert {ws.id for ws in result.workspaces} == {ws_other_org.id}

    def test_admin_sees_all_workspaces(self):
        admin_id = uuid4()
        owner_a = uuid4()
        owner_b = uuid4()

        ws_a = _workspace(
            name="Owner A Private",
            owner_user_id=owner_a,
            visibility=WorkspaceVisibility.PRIVATE,
        )
        ws_b = _workspace(
            name="Owner B Org",
            owner_user_id=owner_b,
            visibility=WorkspaceVisibility.ORG_READ,
        )

        repo = FakeWorkspaceRepository([ws_a, ws_b])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(actor=_actor(admin_id, UserRole.ADMIN))

        assert result.error is None
        assert {ws.id for ws in result.workspaces} == {ws_a.id, ws_b.id}

    def test_admin_can_filter_by_specific_owner(self):
        admin_id = uuid4()
        owner_a = uuid4()
        owner_b = uuid4()

        ws_a = _workspace(name="Owner A Workspace", owner_user_id=owner_a)
        ws_b = _workspace(name="Owner B Workspace", owner_user_id=owner_b)

        repo = FakeWorkspaceRepository([ws_a, ws_b])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(
            actor=_actor(admin_id, UserRole.ADMIN), owner_user_id=owner_a
        )

        assert result.error is None
        assert len(result.workspaces) == 1
        assert result.workspaces[0].id == ws_a.id


# =============================================================================
# GET WORKSPACE - POLICY ENFORCEMENT
# =============================================================================


class TestGetWorkspaceV6:
    """v6: EMPLOYEE can get OWN, ORG_READ, and SHARED(if in ACL)."""

    def test_employee_can_get_own_private_workspace(self):
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

    def test_employee_can_get_org_read_workspace_owned_by_other(self):
        employee_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Org Visible",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.ORG_READ,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.id == ws.id

    def test_employee_cannot_get_foreign_private_workspace(self):
        employee_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Other Private",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.PRIVATE,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.FORBIDDEN

    def test_employee_can_get_shared_workspace_if_member(self):
        employee_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Shared",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.SHARED,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository({ws.id: [employee_id]})
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.id == ws.id

    def test_employee_cannot_get_shared_workspace_if_not_member(self):
        employee_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Shared",
            owner_user_id=other_owner,
            visibility=WorkspaceVisibility.SHARED,
        )

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository({ws.id: [uuid4()]})
        use_case = GetWorkspaceUseCase(repo, acl_repo)

        result = use_case.execute(ws.id, _actor(employee_id, UserRole.EMPLOYEE))

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.FORBIDDEN

    def test_admin_can_get_any_workspace(self):
        admin_id = uuid4()
        other_owner = uuid4()
        ws = _workspace(
            name="Other Private",
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


class TestCreateWorkspaceOwnerRules:
    """v6: workspace provisioning is admin-only (ADR-009)."""

    def test_employee_cannot_create_workspace(self):
        employee_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="My Workspace",
                actor=_actor(employee_id, UserRole.EMPLOYEE),
            )
        )

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.FORBIDDEN

    def test_employee_cannot_assign_owner_to_another_user(self):
        employee_id = uuid4()
        target_owner = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Sneaky Workspace",
                actor=_actor(employee_id, UserRole.EMPLOYEE),
                owner_user_id=target_owner,  # must be ignored
            )
        )

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.FORBIDDEN

    def test_admin_can_assign_owner_to_another_user(self):
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
        admin_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Admin Workspace",
                actor=_actor(admin_id, UserRole.ADMIN),
            )
        )

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.owner_user_id == admin_id
