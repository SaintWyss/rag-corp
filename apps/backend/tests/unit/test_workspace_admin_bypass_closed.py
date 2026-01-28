"""Regression: USER-only guards must deny SERVICE (API key) principals.

This test does NOT call require_principal() to avoid loading Settings (database_url, etc).
We only validate the guard behavior against a mocked request.state.principal.
"""

from types import SimpleNamespace

import pytest
from app.identity.dual_auth import (
    Principal,
    PrincipalType,
    ServicePrincipal,
    require_user_admin,
)
from fastapi import HTTPException

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_service_principal_is_denied_by_require_user_admin():
    dep = require_user_admin()

    req = SimpleNamespace(
        state=SimpleNamespace(
            principal=Principal(
                principal_type=PrincipalType.SERVICE,
                service=ServicePrincipal(
                    api_key_hash="x",
                    permissions=set(),
                    rbac_role="admin",
                ),
            )
        )
    )

    with pytest.raises(HTTPException) as e:
        await dep(req)

    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_principal_is_noop():
    """If principal is missing (auth disabled), guard does nothing (backwards-compatible)."""
    dep = require_user_admin()
    req = SimpleNamespace(state=SimpleNamespace())  # no principal

    await dep(req)
