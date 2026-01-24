"""
Name: Workspace Use Case Tests

Responsibilities:
  - Validate workspace use cases and access policy wiring
  - Cover read/write/ACL decision matrix
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.archive_workspace import ArchiveWorkspaceUseCase
from app.application.use_cases.create_workspace import (
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
)
from app.application.use_cases.get_workspace import GetWorkspaceUseCase
from app.application.use_cases.list_workspaces import ListWorkspacesUseCase
from app.application.use_cases.publish_workspace import PublishWorkspaceUseCase
from app.application.use_cases.share_workspace import ShareWorkspaceUseCase
from app.application.use_cases.update_workspace import UpdateWorkspaceUseCase
from app.application.use_cases.workspace_results import WorkspaceErrorCode
from app.domain.entities import Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole


pytestmark = pytest.mark.unit


class FakeWorkspaceRepository:
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

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: WorkspaceVisibility | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Workspace | None:
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


class FakeWorkspaceAclRepository:
    def __init__(self, acl: dict[UUID, list[UUID]] | None = None):
        self._acl = acl or {}

    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        return list(self._acl.get(workspace_id, []))

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: list[UUID]) -> None:
        unique = list(dict.fromkeys(user_ids))
        self._acl[workspace_id] = unique


class FakeDocumentRepository:
    def __init__(self) -> None:
        self.soft_deleted_workspace_ids: list[UUID] = []

    def soft_delete_documents_by_workspace(self, workspace_id: UUID) -> int:
        self.soft_deleted_workspace_ids.append(workspace_id)
        return 1


def _actor(user_id: UUID, role: UserRole) -> WorkspaceActor:
    return WorkspaceActor(user_id=user_id, role=role)


def _workspace(
    *,
    name: str,
    owner_user_id: UUID,
    visibility: WorkspaceVisibility,
    description: str | None = None,
    archived_at: datetime | None = None,
) -> Workspace:
    return Workspace(
        id=uuid4(),
        name=name,
        visibility=visibility,
        owner_user_id=owner_user_id,
        description=description,
        archived_at=archived_at,
    )


def test_create_workspace_defaults_private_and_owner():
    owner_id = uuid4()
    repo = FakeWorkspaceRepository()
    use_case = CreateWorkspaceUseCase(repository=repo)

    result = use_case.execute(
        CreateWorkspaceInput(
            name="Finance",
            description="Q1 budgets",
            actor=_actor(owner_id, UserRole.EMPLOYEE),
        )
    )

    assert result.error is None
    assert result.workspace is not None
    assert result.workspace.owner_user_id == owner_id
    assert result.workspace.visibility == WorkspaceVisibility.PRIVATE
    assert result.workspace.description == "Q1 budgets"


def test_create_workspace_validates_visibility_and_name():
    owner_id = uuid4()
    repo = FakeWorkspaceRepository()
    use_case = CreateWorkspaceUseCase(repository=repo)

    invalid_name = use_case.execute(
        CreateWorkspaceInput(name="  ", actor=_actor(owner_id, UserRole.ADMIN))
    )
    assert invalid_name.error.code == WorkspaceErrorCode.VALIDATION_ERROR

    invalid_visibility = use_case.execute(
        CreateWorkspaceInput(
            name="HR",
            actor=_actor(owner_id, UserRole.ADMIN),
            visibility=WorkspaceVisibility.ORG_READ,
        )
    )
    assert invalid_visibility.error.code == WorkspaceErrorCode.VALIDATION_ERROR


def test_create_workspace_detects_conflict():
    owner_id = uuid4()
    existing = _workspace(
        name="Ops", owner_user_id=owner_id, visibility=WorkspaceVisibility.PRIVATE
    )
    repo = FakeWorkspaceRepository([existing])
    use_case = CreateWorkspaceUseCase(repository=repo)

    result = use_case.execute(
        CreateWorkspaceInput(
            name="Ops",
            actor=_actor(owner_id, UserRole.ADMIN),
        )
    )

    assert result.error.code == WorkspaceErrorCode.CONFLICT


@dataclass(frozen=True)
class ReadCase:
    name: str
    role: UserRole | None
    actor_id: UUID | None
    visibility: WorkspaceVisibility
    shared_ids: list[UUID]
    expected_allowed: bool


def test_get_workspace_policy_matrix():
    owner_id = uuid4()
    admin_id = uuid4()
    employee_id = uuid4()
    shared_member = uuid4()

    cases = [
        ReadCase(
            name="admin_private",
            role=UserRole.ADMIN,
            actor_id=admin_id,
            visibility=WorkspaceVisibility.PRIVATE,
            shared_ids=[],
            expected_allowed=True,
        ),
        ReadCase(
            name="owner_private",
            role=UserRole.EMPLOYEE,
            actor_id=owner_id,
            visibility=WorkspaceVisibility.PRIVATE,
            shared_ids=[],
            expected_allowed=True,
        ),
        ReadCase(
            name="employee_private",
            role=UserRole.EMPLOYEE,
            actor_id=employee_id,
            visibility=WorkspaceVisibility.PRIVATE,
            shared_ids=[],
            expected_allowed=False,
        ),
        ReadCase(
            name="employee_org_read",
            role=UserRole.EMPLOYEE,
            actor_id=employee_id,
            visibility=WorkspaceVisibility.ORG_READ,
            shared_ids=[],
            expected_allowed=True,
        ),
        ReadCase(
            name="employee_shared_member",
            role=UserRole.EMPLOYEE,
            actor_id=shared_member,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member],
            expected_allowed=True,
        ),
        ReadCase(
            name="employee_shared_non_member",
            role=UserRole.EMPLOYEE,
            actor_id=employee_id,
            visibility=WorkspaceVisibility.SHARED,
            shared_ids=[shared_member],
            expected_allowed=False,
        ),
    ]

    for case in cases:
        workspace = _workspace(
            name="Ops",
            owner_user_id=owner_id,
            visibility=case.visibility,
        )
        repo = FakeWorkspaceRepository([workspace])
        acl_repo = FakeWorkspaceAclRepository({workspace.id: case.shared_ids})
        use_case = GetWorkspaceUseCase(repo, acl_repo)
        actor = (
            None
            if case.role is None
            else WorkspaceActor(user_id=case.actor_id, role=case.role)
        )

        result = use_case.execute(workspace.id, actor)
        if case.expected_allowed:
            assert result.error is None, case.name
            assert result.workspace is not None, case.name
        else:
            assert result.error is not None, case.name
            assert result.error.code == WorkspaceErrorCode.FORBIDDEN, case.name


def test_list_workspaces_filters_by_policy():
    owner_id = uuid4()
    other_owner = uuid4()
    shared_member = uuid4()

    ws_private = _workspace(
        name="Private",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.PRIVATE,
    )
    ws_org = _workspace(
        name="Org",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.ORG_READ,
    )
    ws_shared = _workspace(
        name="Shared",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.SHARED,
    )
    ws_other = _workspace(
        name="Other",
        owner_user_id=other_owner,
        visibility=WorkspaceVisibility.PRIVATE,
    )
    repo = FakeWorkspaceRepository([ws_private, ws_org, ws_shared, ws_other])
    acl_repo = FakeWorkspaceAclRepository({ws_shared.id: [shared_member]})
    use_case = ListWorkspacesUseCase(repo, acl_repo)

    member_result = use_case.execute(actor=_actor(shared_member, UserRole.EMPLOYEE))
    assert {ws.id for ws in member_result.workspaces} == {
        ws_org.id,
        ws_shared.id,
    }

    owner_result = use_case.execute(actor=_actor(owner_id, UserRole.EMPLOYEE))
    assert {ws.id for ws in owner_result.workspaces} == {
        ws_private.id,
        ws_org.id,
        ws_shared.id,
    }

    forbidden = use_case.execute(actor=None)
    assert forbidden.error.code == WorkspaceErrorCode.FORBIDDEN


def test_update_workspace_validates_and_checks_conflict():
    owner_id = uuid4()
    other_owner = uuid4()
    existing = _workspace(
        name="Ops",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.PRIVATE,
    )
    conflict = _workspace(
        name="HR",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.PRIVATE,
    )
    repo = FakeWorkspaceRepository([existing, conflict])
    use_case = UpdateWorkspaceUseCase(repository=repo)

    invalid = use_case.execute(existing.id, _actor(owner_id, UserRole.EMPLOYEE))
    assert invalid.error.code == WorkspaceErrorCode.VALIDATION_ERROR

    forbidden = use_case.execute(
        existing.id,
        _actor(other_owner, UserRole.EMPLOYEE),
        name="Ops-2",
    )
    assert forbidden.error.code == WorkspaceErrorCode.FORBIDDEN

    conflict_result = use_case.execute(
        existing.id,
        _actor(owner_id, UserRole.EMPLOYEE),
        name="HR",
    )
    assert conflict_result.error.code == WorkspaceErrorCode.CONFLICT

    updated = use_case.execute(
        existing.id,
        _actor(owner_id, UserRole.ADMIN),
        name="Ops-Updated",
        description="Updated",
    )
    assert updated.error is None
    assert updated.workspace.name == "Ops-Updated"
    assert updated.workspace.description == "Updated"


def test_get_workspace_not_found_when_archived():
    owner_id = uuid4()
    archived = _workspace(
        name="Archived",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.PRIVATE,
        archived_at=datetime.now(timezone.utc),
    )
    repo = FakeWorkspaceRepository([archived])
    acl_repo = FakeWorkspaceAclRepository()
    use_case = GetWorkspaceUseCase(repo, acl_repo)

    result = use_case.execute(archived.id, _actor(owner_id, UserRole.ADMIN))
    assert result.error.code == WorkspaceErrorCode.NOT_FOUND


def test_publish_share_and_archive_use_cases():
    owner_id = uuid4()
    outsider_id = uuid4()
    shared_user = uuid4()
    workspace = _workspace(
        name="Docs",
        owner_user_id=owner_id,
        visibility=WorkspaceVisibility.PRIVATE,
    )
    repo = FakeWorkspaceRepository([workspace])
    acl_repo = FakeWorkspaceAclRepository()

    publish = PublishWorkspaceUseCase(repository=repo)
    published = publish.execute(workspace.id, _actor(owner_id, UserRole.EMPLOYEE))
    assert published.error is None
    assert published.workspace.visibility == WorkspaceVisibility.ORG_READ
    forbidden_publish = publish.execute(
        workspace.id, _actor(outsider_id, UserRole.EMPLOYEE)
    )
    assert forbidden_publish.error.code == WorkspaceErrorCode.FORBIDDEN

    share = ShareWorkspaceUseCase(repo, acl_repo)
    empty_acl = share.execute(
        workspace.id,
        _actor(owner_id, UserRole.EMPLOYEE),
        user_ids=[],
    )
    assert empty_acl.error.code == WorkspaceErrorCode.VALIDATION_ERROR
    shared = share.execute(
        workspace.id,
        _actor(owner_id, UserRole.EMPLOYEE),
        user_ids=[shared_user],
    )
    assert shared.error is None
    assert shared.workspace.visibility == WorkspaceVisibility.SHARED
    assert acl_repo.list_workspace_acl(workspace.id) == [shared_user]

    doc_repo = FakeDocumentRepository()
    archive = ArchiveWorkspaceUseCase(repository=repo, document_repository=doc_repo)
    forbidden_archive = archive.execute(
        workspace.id, _actor(outsider_id, UserRole.EMPLOYEE)
    )
    assert forbidden_archive.error.code == WorkspaceErrorCode.FORBIDDEN
    archived = archive.execute(workspace.id, _actor(owner_id, UserRole.EMPLOYEE))
    assert archived.error is None
    assert archived.archived is True
    assert doc_repo.soft_deleted_workspace_ids == [workspace.id]
