"""
Unit tests for audit event helpers.
"""

from uuid import uuid4

import pytest

from app.audit import emit_audit_event
from app.domain.audit import AuditEvent


pytestmark = pytest.mark.unit


class _CaptureRepo:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record_event(self, event: AuditEvent) -> None:
        self.events.append(event)


def test_emit_audit_event_includes_workspace_id() -> None:
    repo = _CaptureRepo()
    workspace_id = uuid4()

    emit_audit_event(
        repo,
        action="workspaces.create",
        workspace_id=workspace_id,
    )

    assert len(repo.events) == 1
    event = repo.events[0]
    assert event.action == "workspaces.create"
    assert event.metadata["workspace_id"] == str(workspace_id)
    assert event.metadata["principal_type"] == "anonymous"
