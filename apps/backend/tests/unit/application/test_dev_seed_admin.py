"""
Tests for dev_seed_admin module.

Validates:
  - Disabled when config says so
  - Fail-fast when not in local environment
  - Creates user when missing
  - Idempotent when user exists
  - Force reset behavior
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.application.dev_seed_admin import ensure_dev_admin
from app.crosscutting.config import Settings
from app.identity.users import UserRole

pytestmark = pytest.mark.unit


class FakeUserRecord:
    """Minimal user-like object for testing."""

    def __init__(self, *, user_id=None, email="test@local"):
        self.id = user_id or uuid4()
        self.email = email


def _make_settings(**overrides):
    """Create Settings with sensible defaults for testing."""
    defaults = {
        "database_url": "postgresql://test:test@localhost/test",
        "app_env": "local",
        "jwt_secret": "test-secret",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _dummy_hasher(password: str) -> str:
    return f"hashed:{password}"


def test_ensure_dev_admin_disabled():
    """When dev_seed_admin=False, nothing should happen."""
    repo = MagicMock()
    settings = _make_settings(dev_seed_admin=False)

    ensure_dev_admin(settings, user_repo=repo, password_hasher=_dummy_hasher, env={})

    repo.get_user_by_email.assert_not_called()
    repo.create_user.assert_not_called()
    repo.update_user.assert_not_called()


def test_ensure_dev_admin_fail_fast_if_not_local():
    """When app_env != local (and not E2E), should fail fast."""
    repo = MagicMock()

    settings = _make_settings(
        dev_seed_admin=True,
        dev_seed_admin_email="test@local",
        dev_seed_admin_password="pass",
        app_env="development",
    )

    with pytest.raises(RuntimeError, match="must be 'local'"):
        ensure_dev_admin(
            settings, user_repo=repo, password_hasher=_dummy_hasher, env={}
        )


def test_ensure_dev_admin_create_new():
    """When user doesn't exist, should create it."""
    repo = MagicMock()
    repo.get_user_by_email.return_value = None

    settings = _make_settings(
        dev_seed_admin=True,
        dev_seed_admin_email="test@local",
        dev_seed_admin_password="pass",
        dev_seed_admin_role="admin",
    )

    ensure_dev_admin(settings, user_repo=repo, password_hasher=_dummy_hasher, env={})

    repo.get_user_by_email.assert_called_once_with("test@local")
    repo.create_user.assert_called_once()
    repo.update_user.assert_not_called()

    # Verify create_user arguments
    call_kwargs = repo.create_user.call_args.kwargs
    assert call_kwargs["email"] == "test@local"
    assert call_kwargs["role"] == UserRole.ADMIN
    assert call_kwargs["is_active"] is True
    assert "hashed:" in call_kwargs["password_hash"]


def test_ensure_dev_admin_idempotent_existing():
    """When user exists and no force_reset, should skip."""
    existing = FakeUserRecord(email="test@local")
    repo = MagicMock()
    repo.get_user_by_email.return_value = existing

    settings = _make_settings(
        dev_seed_admin=True,
        dev_seed_admin_email="test@local",
        dev_seed_admin_password="pass",
        dev_seed_admin_force_reset=False,
    )

    ensure_dev_admin(settings, user_repo=repo, password_hasher=_dummy_hasher, env={})

    repo.get_user_by_email.assert_called_once_with("test@local")
    repo.create_user.assert_not_called()
    repo.update_user.assert_not_called()


def test_ensure_dev_admin_force_reset():
    """When force_reset=True, should update existing user."""
    existing = FakeUserRecord(email="test@local")
    repo = MagicMock()
    repo.get_user_by_email.return_value = existing

    settings = _make_settings(
        dev_seed_admin=True,
        dev_seed_admin_email="test@local",
        dev_seed_admin_password="newpass",
        dev_seed_admin_force_reset=True,
        dev_seed_admin_role="admin",
    )

    ensure_dev_admin(settings, user_repo=repo, password_hasher=_dummy_hasher, env={})

    repo.get_user_by_email.assert_called_once_with("test@local")
    repo.create_user.assert_not_called()
    repo.update_user.assert_called_once()

    call_args = repo.update_user.call_args
    assert call_args.args[0] == existing.id
    call_kwargs = call_args.kwargs
    assert call_kwargs["role"] == UserRole.ADMIN
    assert call_kwargs["is_active"] is True
    assert "hashed:" in call_kwargs["password_hash"]
