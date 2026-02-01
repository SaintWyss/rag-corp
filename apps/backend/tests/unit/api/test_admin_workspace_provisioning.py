"""
Name: Admin Workspace Provisioning Tests (ADR-009)

Responsibilities:
  - Validate admin can create workspaces for other users
  - Validate admin can list workspaces by owner
  - Validate employee cannot access admin endpoints (403)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.application.usecases.workspace.create_workspace import (
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
)
from app.application.usecases.workspace.list_workspaces import ListWorkspacesUseCase
from app.application.usecases.workspace.workspace_results import WorkspaceErrorCode
from app.domain.entities import Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

pytestmark = pytest.mark.unit


# =============================================================================
# FAKE REPOSITORIES
# =============================================================================


class FakeWorkspaceRepository:
    """Minimal fake for testing admin provisioning."""

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


# =============================================================================
# HELPERS
# =============================================================================


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
# ADMIN CREATE WORKSPACE FOR USER
# =============================================================================


class TestAdminCreateWorkspaceForUser:
    """ADR-009: Admin can create workspaces for other users."""

    def test_admin_creates_workspace_for_another_user(self):
        """Admin can create a workspace and assign it to another user."""
        admin_id = uuid4()
        target_user_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Target User Workspace",
                description="Created by admin for target user",
                actor=_actor(admin_id, UserRole.ADMIN),
                owner_user_id=target_user_id,  # Assign to different user
            )
        )

        assert result.error is None
        assert result.workspace is not None
        assert result.workspace.owner_user_id == target_user_id
        assert result.workspace.name == "Target User Workspace"

    def test_admin_can_create_multiple_workspaces_for_same_user(self):
        """Admin can create multiple workspaces for the same user."""
        admin_id = uuid4()
        target_user_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        # Create first workspace
        result1 = use_case.execute(
            CreateWorkspaceInput(
                name="Workspace One",
                actor=_actor(admin_id, UserRole.ADMIN),
                owner_user_id=target_user_id,
            )
        )
        assert result1.error is None

        # Create second workspace
        result2 = use_case.execute(
            CreateWorkspaceInput(
                name="Workspace Two",
                actor=_actor(admin_id, UserRole.ADMIN),
                owner_user_id=target_user_id,
            )
        )
        assert result2.error is None

        # Both exist
        assert result1.workspace.owner_user_id == target_user_id
        assert result2.workspace.owner_user_id == target_user_id

    def test_admin_cannot_create_duplicate_name_for_same_owner(self):
        """Admin cannot create two workspaces with same name for same owner."""
        admin_id = uuid4()
        target_user_id = uuid4()
        existing = _workspace(name="Existing", owner_user_id=target_user_id)
        repo = FakeWorkspaceRepository([existing])
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Existing",  # Same name
                actor=_actor(admin_id, UserRole.ADMIN),
                owner_user_id=target_user_id,  # Same owner
            )
        )

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.CONFLICT

    def test_employee_cannot_assign_owner_to_another_user(self):
        """Employee cannot create workspaces (admin-only provisioning)."""
        employee_id = uuid4()
        target_user_id = uuid4()
        repo = FakeWorkspaceRepository()
        use_case = CreateWorkspaceUseCase(repository=repo)

        result = use_case.execute(
            CreateWorkspaceInput(
                name="Sneaky Workspace",
                actor=_actor(employee_id, UserRole.EMPLOYEE),
                owner_user_id=target_user_id,  # Try to assign to another user
            )
        )

        assert result.error is not None
        assert result.error.code == WorkspaceErrorCode.FORBIDDEN


# =============================================================================
# ADMIN LIST WORKSPACES BY OWNER
# =============================================================================


class TestAdminListWorkspacesByOwner:
    """ADR-008: Admin can list workspaces filtered by owner."""

    def test_admin_lists_workspaces_for_specific_user(self):
        """Admin can filter workspaces by owner_user_id."""
        admin_id = uuid4()
        user_a = uuid4()
        user_b = uuid4()

        ws_a = _workspace(name="User A Workspace", owner_user_id=user_a)
        ws_b = _workspace(name="User B Workspace", owner_user_id=user_b)

        repo = FakeWorkspaceRepository([ws_a, ws_b])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(
            actor=_actor(admin_id, UserRole.ADMIN),
            owner_user_id=user_a,  # Filter to user_a only
        )

        assert result.error is None
        assert len(result.workspaces) == 1
        assert result.workspaces[0].id == ws_a.id

    def test_admin_lists_all_workspaces_without_filter(self):
        """Admin can list all workspaces (no owner filter)."""
        admin_id = uuid4()
        user_a = uuid4()
        user_b = uuid4()

        ws_a = _workspace(name="User A Workspace", owner_user_id=user_a)
        ws_b = _workspace(name="User B Workspace", owner_user_id=user_b)

        repo = FakeWorkspaceRepository([ws_a, ws_b])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(
            actor=_actor(admin_id, UserRole.ADMIN),
            owner_user_id=None,  # No filter
        )

        assert result.error is None
        assert len(result.workspaces) == 2

    def test_admin_lists_user_with_no_workspaces(self):
        """Admin listing workspaces for user with none returns empty list."""
        admin_id = uuid4()
        user_with_workspaces = uuid4()
        user_without = uuid4()

        ws = _workspace(name="Some Workspace", owner_user_id=user_with_workspaces)

        repo = FakeWorkspaceRepository([ws])
        acl_repo = FakeWorkspaceAclRepository()
        use_case = ListWorkspacesUseCase(repo, acl_repo)

        result = use_case.execute(
            actor=_actor(admin_id, UserRole.ADMIN),
            owner_user_id=user_without,  # This user has no workspaces
        )

        assert result.error is None
        assert len(result.workspaces) == 0


# =============================================================================
# ENDPOINT GUARD VERIFICATION
# =============================================================================


class TestAdminEndpointGuards:
    """Verify admin endpoint guards are correctly configured."""

    def test_admin_routes_file_has_correct_guards(self):
        """Verify admin_routes.py uses require_admin() and require_principal(ADMIN_CONFIG)."""
        from pathlib import Path

        routes_path = (
            Path(__file__).resolve().parents[3] / "app" / "api" / "admin_routes.py"
        )

        if not routes_path.exists():
            pytest.skip("admin_routes.py not found")

        content = routes_path.read_text()

        # Check that endpoints use correct guards
        assert "require_admin()" in content, "Admin routes should use require_admin()"
        assert "require_principal(Permission.ADMIN_CONFIG)" in content, (
            "Admin routes should require ADMIN_CONFIG permission"
        )

    def test_admin_routes_registered_in_main(self):
        """Verify admin routes are registered in main.py."""
        from pathlib import Path

        main_path = Path(__file__).resolve().parents[3] / "app" / "api" / "main.py"
        content = main_path.read_text()

        assert "admin_routes" in content or "admin_router" in content, (
            "Admin routes should be registered in main.py"
        )
