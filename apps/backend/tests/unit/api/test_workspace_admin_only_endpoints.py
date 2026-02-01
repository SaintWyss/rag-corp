"""Verify workspace routes use USER-only role guards (API keys denied)."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _backend_root() -> Path:
    """
    This test lives at:
      apps/backend/tests/unit/test_workspace_admin_only_endpoints.py

    So backend root is 3 levels up:
      tests/unit -> tests -> backend root
    """
    return Path(__file__).resolve().parents[2]


def _read(rel_path_from_backend_root: str) -> str:
    return (_backend_root() / rel_path_from_backend_root).read_text(encoding="utf-8")


def _extract_function_block(source: str, func_name: str, max_lines: int = 160) -> str:
    lines = source.splitlines()
    needle = f"def {func_name}("
    async_needle = f"async def {func_name}("
    for i, line in enumerate(lines):
        if line.startswith(needle) or line.startswith(async_needle):
            return "\n".join(lines[i : i + max_lines])
    raise AssertionError(f"Function not found: {func_name}")


def test_workspace_write_endpoints_are_user_admin_only():
    """
    Workspace write/admin endpoints MUST be USER-only admin guarded:
      - Depends(require_user_admin())
    """
    src = _read("app/interfaces/api/http/routes.py")
    expectations = [
        ("create_workspace", "Permission.DOCUMENTS_CREATE"),
        ("update_workspace", "Permission.DOCUMENTS_CREATE"),
        ("publish_workspace", "Permission.DOCUMENTS_CREATE"),
        ("share_workspace", "Permission.DOCUMENTS_CREATE"),
        ("archive_workspace_action", "Permission.DOCUMENTS_DELETE"),
        ("archive_workspace", "Permission.DOCUMENTS_DELETE"),
    ]

    for func, perm in expectations:
        block = _extract_function_block(src, func)
        assert "Depends(require_user_admin())" in block, block
        assert perm in block, block


def test_workspace_read_endpoints_are_user_employee_or_admin_only():
    """
    Workspace read endpoints MUST be USER-only employee/admin guarded:
      - Depends(require_user_employee_or_admin())
    """
    src = _read("app/interfaces/api/http/routes.py")
    expectations = [
        ("list_workspaces", "Permission.DOCUMENTS_READ"),
        ("get_workspace", "Permission.DOCUMENTS_READ"),
    ]

    for func, perm in expectations:
        block = _extract_function_block(src, func)
        assert "Depends(require_user_employee_or_admin())" in block, block
        assert perm in block, block


def test_user_only_guard_helpers_exist():
    src = _read("app/identity/dual_auth.py")
    assert "def require_user_roles" in src
    assert "def require_user_admin" in src
    assert "def require_user_employee_or_admin" in src


def test_role_matrix_for_key_workspace_endpoints():
    """
    Enforce the role matrix for key endpoints:
      - Admin-only user endpoints use require_user_admin()
      - Employee/Admin endpoints use require_user_employee_or_admin()
      - Service/API endpoints use require_employee_or_admin()
    """
    src = _read("app/interfaces/api/http/routes.py")

    admin_only = [
        "create_workspace",
        "update_workspace",
        "publish_workspace",
        "share_workspace",
        "archive_workspace_action",
        "archive_workspace",
    ]
    employee_or_admin = [
        "list_workspaces",
        "get_workspace",
    ]
    service_allowed = [
        "upload_workspace_document",
        "reprocess_workspace_document",
        "query_workspace",
        "ask_workspace",
        "ask_workspace_stream",
    ]

    for func in admin_only:
        block = _extract_function_block(src, func)
        assert "Depends(require_user_admin())" in block, block

    for func in employee_or_admin:
        block = _extract_function_block(src, func)
        assert "Depends(require_user_employee_or_admin())" in block, block

    for func in service_allowed:
        block = _extract_function_block(src, func)
        assert "Depends(require_employee_or_admin())" in block, block
        assert "require_user_" not in block, block
