"""
Name: Workspace Admin-Only Endpoint Tests (ADR-008)

Responsibilities:
  - Verify that workspace write endpoints use require_admin() guard
  - Verify that workspace read endpoints use require_employee_or_admin() guard
  - Document ADR-008 compliance for workspace access
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _get_routes_content() -> str:
    """Load routes.py content for inspection."""
    routes_path = (
        Path(__file__).parent.parent.parent
        / "app"
        / "interfaces"
        / "api"
        / "http"
        / "routes.py"
    )
    return routes_path.read_text()


# =============================================================================
# ENDPOINT GUARD VERIFICATION
# =============================================================================


class TestWorkspaceWriteEndpointsRequireAdmin:
    """
    ADR-008: All workspace write endpoints must use require_admin() guard.

    Employees are NOT allowed to:
    - Create workspaces
    - Update workspaces
    - Publish workspaces
    - Share workspaces
    - Archive workspaces
    - Delete workspaces
    """

    def test_create_workspace_requires_admin(self):
        """POST /workspaces uses require_admin()"""
        content = _get_routes_content()
        match = re.search(r'@router\.post\(\s*"/workspaces"', content)
        assert match, "Could not find POST /workspaces endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 500]

        assert (
            "require_admin()" in endpoint_block
        ), "POST /workspaces should use require_admin()"
        assert (
            "require_employee_or_admin()" not in endpoint_block[:400]
        ), "POST /workspaces should NOT use require_employee_or_admin()"

    def test_update_workspace_requires_admin(self):
        """PATCH /workspaces/{id} uses require_admin()"""
        content = _get_routes_content()
        match = re.search(r'@router\.patch\(\s*"/workspaces/\{workspace_id\}"', content)
        assert match, "Could not find PATCH /workspaces/{id} endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 500]

        assert (
            "require_admin()" in endpoint_block
        ), "PATCH /workspaces/{id} should use require_admin()"

    def test_publish_workspace_requires_admin(self):
        """POST /workspaces/{id}/publish uses require_admin()"""
        content = _get_routes_content()
        match = re.search(
            r'@router\.post\(\s*"/workspaces/\{workspace_id\}/publish"', content
        )
        assert match, "Could not find POST /workspaces/{id}/publish endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 500]

        assert (
            "require_admin()" in endpoint_block
        ), "POST /workspaces/{id}/publish should use require_admin()"

    def test_share_workspace_requires_admin(self):
        """POST /workspaces/{id}/share uses require_admin()"""
        content = _get_routes_content()
        match = re.search(
            r'@router\.post\(\s*"/workspaces/\{workspace_id\}/share"', content
        )
        assert match, "Could not find POST /workspaces/{id}/share endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 500]

        assert (
            "require_admin()" in endpoint_block
        ), "POST /workspaces/{id}/share should use require_admin()"

    def test_archive_workspace_action_requires_admin(self):
        """POST /workspaces/{id}/archive uses require_admin()"""
        content = _get_routes_content()
        match = re.search(
            r'@router\.post\(\s*"/workspaces/\{workspace_id\}/archive"', content
        )
        assert match, "Could not find POST /workspaces/{id}/archive endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 500]

        assert (
            "require_admin()" in endpoint_block
        ), "POST /workspaces/{id}/archive should use require_admin()"

    def test_delete_workspace_requires_admin(self):
        """DELETE /workspaces/{id} uses require_admin()"""
        content = _get_routes_content()
        match = re.search(
            r'@router\.delete\(\s*"/workspaces/\{workspace_id\}"', content
        )
        assert match, "Could not find DELETE /workspaces/{id} endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 500]

        assert (
            "require_admin()" in endpoint_block
        ), "DELETE /workspaces/{id} should use require_admin()"


class TestWorkspaceReadEndpointsAllowEmployees:
    """
    ADR-008: Workspace read endpoints must allow employees (owner-only enforced at use case level).
    """

    def test_list_workspaces_allows_employee(self):
        """GET /workspaces uses require_employee_or_admin()"""
        content = _get_routes_content()
        match = re.search(r'@router\.get\(\s*"/workspaces"', content)
        assert match, "Could not find GET /workspaces endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 400]

        assert (
            "require_employee_or_admin()" in endpoint_block
        ), "GET /workspaces should use require_employee_or_admin()"

    def test_get_workspace_allows_employee(self):
        """GET /workspaces/{id} uses require_employee_or_admin()"""
        content = _get_routes_content()
        match = re.search(r'@router\.get\(\s*"/workspaces/\{workspace_id\}"', content)
        assert match, "Could not find GET /workspaces/{id} endpoint"

        start_pos = match.end()
        endpoint_block = content[start_pos : start_pos + 400]

        assert (
            "require_employee_or_admin()" in endpoint_block
        ), "GET /workspaces/{id} should use require_employee_or_admin()"


# =============================================================================
# ADR-008 COMPLIANCE DOCUMENTATION
# =============================================================================


class TestADR008WorkspaceAccessRules:
    """Documentation tests for ADR-008 workspace access rules."""

    def test_employee_access_rules(self):
        """
        ADR-008 Employee Access Rules:

        ALLOWED:
        - GET /workspaces (list - filtered to owned workspaces at use case level)
        - GET /workspaces/{id} (get - must own or have shared access)

        FORBIDDEN (403):
        - POST /workspaces (create)
        - PATCH /workspaces/{id} (update)
        - POST /workspaces/{id}/publish
        - POST /workspaces/{id}/share
        - POST /workspaces/{id}/archive
        - DELETE /workspaces/{id}
        """
        from app.identity.users import UserRole

        assert UserRole.EMPLOYEE.value == "employee"

    def test_admin_access_rules(self):
        """
        ADR-008 Admin Access Rules:

        ALLOWED (all operations):
        - GET /workspaces (list all)
        - GET /workspaces/{id} (get any)
        - POST /workspaces (create, optionally assign to other user)
        - PATCH /workspaces/{id} (update any)
        - POST /workspaces/{id}/publish (publish any)
        - POST /workspaces/{id}/share (share any)
        - POST /workspaces/{id}/archive (archive any)
        - DELETE /workspaces/{id} (delete any)
        """
        from app.identity.users import UserRole

        assert UserRole.ADMIN.value == "admin"

    def test_guard_functions_exist(self):
        """Verify that the guard functions are properly defined."""
        from app.identity.dual_auth import require_admin, require_employee_or_admin

        # Both should be callable factories
        assert callable(require_admin)
        assert callable(require_employee_or_admin)

        # They should return callables (FastAPI dependencies)
        admin_dep = require_admin()
        employee_dep = require_employee_or_admin()
        assert callable(admin_dep)
        assert callable(employee_dep)
