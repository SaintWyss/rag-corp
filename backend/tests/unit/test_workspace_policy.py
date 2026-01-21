"""
Name: Workspace Access Policy Tests

Responsibilities:
  - Validate workspace read/write/ACL access rules
  - Cover role + visibility + membership matrix
"""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class PolicyCase:
    name: str
    role: UserRole | None
    actor_id: UUID | None
    visibility: WorkspaceVisibility
    shared_ids: list[UUID]
    expected_read: bool
    expected_write: bool
    expected_manage: bool


def test_workspace_access_policy_matrix():
    owner_id = uuid4()
    admin_id = uuid4()
    employee_id = uuid4()
    shared_member_id = uuid4()

    cases = [
        PolicyCase(
            name="admin_private",
            role=UserRole.ADMIN,
            actor_id=admin_id,
            visibility=WorkspaceVisibility.PRIVATE,
            shared_ids=[],
            expected_read=True,
            expected_write=True,
            expected_manage=True,
        ),
        PolicyCase(
            name="owner_private",
            role=UserRole.EMPLOYEE,
            actor_id=owner_id,
            visibility=WorkspaceVisibility.PRIVATE,
            shared_ids=[],
            expected_read=True,
            expected_write=True,
            expected_manage=True,
        ),
        PolicyCase(
            name="employee_private",
            role=UserRole.EMPLOYEE,
            actor_id=employee_id,
            visibility=WorkspaceVisibility.PRIVATE,
            shared_ids=[],
            expected_read=False,
            expected_write=False,
            expected_manage=False,
        ),
        PolicyCase(
            name="admin_org_read",
            role=UserRole.ADMIN,
            actor_id=admin_id,
            visibility=WorkspaceVisibility.ORG_READ,
            shared_ids=[],
            expected_read=True,
            expected_write=True,
            expected_manage=True,
        ),
        PolicyCase(
            name="owner_org_read",
            role=UserRole.EMPLOYEE,
            actor_id=owner_id,
            visibility=WorkspaceVisibility.ORG_READ,
            shared_ids=[],
            expected_read=True,
            expected_write=True,
            expected_manage=True,
        ),
        PolicyCase(
            name="employee_org_read",
            role=UserRole.EMPLOYEE,
            actor_id=employee_id,
            visibility=WorkspaceVisibility.ORG_READ,
            shared_ids=[],
            expected_read=True,
            expected_write=False,
            expected_manage=False,
        ),
        PolicyCase(
            name="admin_shared",
            role=UserRole.ADMIN,
            actor_id=admin_id,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member_id],
            expected_read=True,
            expected_write=True,
            expected_manage=True,
        ),
        PolicyCase(
            name="owner_shared",
            role=UserRole.EMPLOYEE,
            actor_id=owner_id,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member_id],
            expected_read=True,
            expected_write=True,
            expected_manage=True,
        ),
        PolicyCase(
            name="employee_shared_member",
            role=UserRole.EMPLOYEE,
            actor_id=shared_member_id,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member_id],
            expected_read=True,
            expected_write=False,
            expected_manage=False,
        ),
        PolicyCase(
            name="employee_shared_non_member",
            role=UserRole.EMPLOYEE,
            actor_id=employee_id,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member_id],
            expected_read=False,
            expected_write=False,
            expected_manage=False,
        ),
        PolicyCase(
            name="unauthenticated_shared",
            role=None,
            actor_id=None,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member_id],
            expected_read=False,
            expected_write=False,
            expected_manage=False,
        ),
    ]

    for case in cases:
        workspace = _workspace(
            owner_user_id=owner_id,
            visibility=case.visibility,
            shared_user_ids=case.shared_ids,
        )
        actor = (
            None
            if case.role is None
            else WorkspaceActor(user_id=case.actor_id, role=case.role)
        )
        read = can_read_workspace(workspace, actor, shared_user_ids=case.shared_ids)
        write = can_write_workspace(workspace, actor)
        manage = can_manage_acl(workspace, actor)

        assert read is case.expected_read, case.name
        assert write is case.expected_write, case.name
        assert manage is case.expected_manage, case.name


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
