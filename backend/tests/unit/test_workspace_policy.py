"""
Name: Workspace Access Policy Tests

Responsibilities:
  - Validate workspace read/write/ACL access rules
  - Cover role + visibility + membership matrix
"""

from uuid import UUID, uuid4

import pytest

from app.domain.entities import Workspace, WorkspaceVisibility
from app.domain.workspace_policy import (
    WorkspaceActor,
    can_manage_acl,
    can_read_workspace,
    can_write_workspace,
)
from app.users import UserRole


pytestmark = pytest.mark.unit


def _workspace(
    *,
    owner_user_id: UUID | None,
    visibility: WorkspaceVisibility,
    shared_user_ids: list[UUID] | None = None,
) -> Workspace:
    return Workspace(
        id=uuid4(),
        name="Workspace",
        owner_user_id=owner_user_id,
        visibility=visibility,
        shared_user_ids=shared_user_ids or [],
    )


def test_workspace_access_policy_matrix():
    owner_id = uuid4()
    admin_id = uuid4()
    employee_id = uuid4()
    roles = {
        "admin": (UserRole.ADMIN, admin_id),
        "owner": (UserRole.EMPLOYEE, owner_id),
        "employee": (UserRole.EMPLOYEE, employee_id),
    }

    for role_name, (role, actor_id) in roles.items():
        for visibility in WorkspaceVisibility:
            for is_member in (True, False):
                shared_ids = [actor_id] if is_member else []
                workspace = _workspace(
                    owner_user_id=owner_id,
                    visibility=visibility,
                    shared_user_ids=shared_ids,
                )
                actor = WorkspaceActor(user_id=actor_id, role=role)

                if role == UserRole.ADMIN or actor_id == owner_id:
                    expected_read = True
                    expected_write = True
                    expected_manage = True
                elif visibility == WorkspaceVisibility.PRIVATE:
                    expected_read = False
                    expected_write = False
                    expected_manage = False
                elif visibility == WorkspaceVisibility.ORG_READ:
                    expected_read = True
                    expected_write = False
                    expected_manage = False
                else:
                    expected_read = is_member
                    expected_write = False
                    expected_manage = False

                label = f"{role_name}_{visibility.value}_member_{is_member}"
                read = can_read_workspace(workspace, actor, shared_user_ids=shared_ids)
                write = can_write_workspace(workspace, actor)
                manage = can_manage_acl(workspace, actor)

                assert read is expected_read, label
                assert write is expected_write, label
                assert manage is expected_manage, label

    shared_workspace = _workspace(
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.SHARED,
        shared_user_ids=[uuid4()],
    )
    assert can_read_workspace(shared_workspace, None) is False
    assert can_write_workspace(shared_workspace, None) is False
    assert can_manage_acl(shared_workspace, None) is False


def test_can_read_workspace_uses_workspace_acl_by_default():
    owner_id = uuid4()
    shared_member_id = uuid4()
    workspace = _workspace(
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.SHARED,
        shared_user_ids=[shared_member_id],
    )
    actor = WorkspaceActor(user_id=shared_member_id, role=UserRole.EMPLOYEE)

    assert can_read_workspace(workspace, actor) is True
