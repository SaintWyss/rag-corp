"""
Name: Dev Seed Admin (Local-only + E2E override)

Responsibilities:
  - Ensure a dev admin user exists when configured
  - Enforce safety guard: only allowed in local environment (unless E2E override)
  - Optionally force reset password/role/active flag for deterministic demos/tests

Architecture:
  - Clean Architecture / Hexagonal
  - Layer: Application task (wired by Infrastructure/composition root)
  - Depends on abstractions (UserPort), not concrete Postgres repos

Patterns:
  - Use-case/task orchestration (seed task)
  - Dependency Injection (repo + hasher + env provider injected)
  - Fail-fast guard (safety boundary)
  - Idempotent provisioning (ensure-* behavior)

SOLID:
  - SRP: only admin seeding logic
  - DIP: does not import infrastructure repositories

CRC:
  Component: ensure_dev_admin
  Responsibilities:
    - Validate environment guard (local-only unless E2E)
    - Resolve seed config (settings vs E2E env)
    - Ensure user exists (create or update if force_reset)
  Collaborators:
    - user_repo (get/create/update)
    - password_hasher
    - Settings + env provider
  Constraints:
    - Must NEVER run in non-local env unless E2E override is enabled
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol
from uuid import UUID

from ..crosscutting.config import Settings
from ..crosscutting.logger import logger
from ..identity.users import UserRole

# -----------------------------
# Ports (duck-typed protocols)
# -----------------------------


class UserRecord(Protocol):
    """R: Minimal shape required by this seed task."""

    id: UUID


class UserPort(Protocol):
    """R: User repository port needed by the seed task."""

    def get_user_by_email(self, email: str) -> UserRecord | None: ...

    def create_user(
        self, *, email: str, password_hash: str, role: UserRole, is_active: bool
    ) -> UserRecord: ...

    def update_user(
        self,
        user_id: UUID,
        *,
        password_hash: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> None: ...


# -----------------------------
# Seed configuration
# -----------------------------


@dataclass(frozen=True, slots=True)
class _AdminSeedSpec:
    """R: Resolved seed configuration (no I/O)."""

    enabled: bool
    is_e2e: bool
    email: str
    password: str
    role: UserRole
    force_reset: bool


def _parse_bool(value: str | None) -> bool:
    """R: Parse common boolean env representations."""
    v = (value or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _resolve_role(role_str: str) -> UserRole:
    """R: Resolve UserRole with safe fallback."""
    try:
        return UserRole((role_str or "").strip().lower())
    except Exception:
        logger.warning(
            "Dev seed admin: invalid role; falling back to ADMIN",
            extra={"role": role_str},
        )
        return UserRole.ADMIN


def _resolve_seed_spec(settings: Settings, env: Mapping[str, str]) -> _AdminSeedSpec:
    """
    R: Resolve seed inputs from (settings) or (E2E env override).
    """
    is_e2e = _parse_bool(env.get("E2E_SEED_ADMIN"))

    # R: Enabled if settings flag OR E2E flag
    enabled = bool(settings.dev_seed_admin) or is_e2e

    if not enabled:
        return _AdminSeedSpec(
            enabled=False,
            is_e2e=is_e2e,
            email="",
            password="",
            role=UserRole.ADMIN,
            force_reset=False,
        )

    if is_e2e:
        email = env.get("E2E_ADMIN_EMAIL", "admin@local")
        password = env.get("E2E_ADMIN_PASSWORD", "admin")
        role = UserRole.ADMIN  # R: keep E2E deterministic
        force_reset = False
    else:
        email = settings.dev_seed_admin_email
        password = settings.dev_seed_admin_password
        role = _resolve_role(settings.dev_seed_admin_role)
        force_reset = bool(settings.dev_seed_admin_force_reset)

    return _AdminSeedSpec(
        enabled=True,
        is_e2e=is_e2e,
        email=email,
        password=password,
        role=role,
        force_reset=force_reset,
    )


def _assert_allowed_environment(settings: Settings, *, is_e2e: bool) -> None:
    """
    R: Safety guard:
      - If NOT E2E: only allow local environment.
      - If E2E: allow other envs because CI might run with different app_env.
    """
    if is_e2e:
        return

    env = (settings.app_env or "").strip().lower()
    if env != "local":
        raise RuntimeError(
            f"FATAL: DEV_SEED_ADMIN is enabled but ENV is '{env}' (must be 'local'). "
            "Safety guard prevents accidental overrides."
        )


def ensure_dev_admin(
    settings: Settings,
    *,
    user_repo: UserPort,
    password_hasher: Callable[[str], str],
    env: Mapping[str, str],
) -> None:
    """
    R: Ensure a development admin user exists if configured.

    Behavior:
      - If disabled: no-op
      - If enabled:
          - Create user if missing
          - If force_reset: update password/role/is_active
          - Otherwise: skip if exists

    Safety:
      - Non-local environments are blocked unless E2E override is enabled.
    """
    spec = _resolve_seed_spec(settings, env)
    if not spec.enabled:
        return

    _assert_allowed_environment(settings, is_e2e=spec.is_e2e)

    logger.info(
        "Dev seed admin: ensuring admin user",
        extra={
            "email": spec.email,
            "role": str(spec.role),
            "force_reset": spec.force_reset,
            "is_e2e": spec.is_e2e,
        },
    )

    existing = user_repo.get_user_by_email(spec.email)

    if existing is None:
        password_hash = password_hasher(spec.password)
        user_repo.create_user(
            email=spec.email,
            password_hash=password_hash,
            role=spec.role,
            is_active=True,
        )
        logger.info(
            "Dev seed admin: user created",
            extra={"email": spec.email, "role": str(spec.role)},
        )
        return

    if spec.force_reset:
        password_hash = password_hasher(spec.password)
        user_repo.update_user(
            existing.id,
            password_hash=password_hash,
            role=spec.role,
            is_active=True,
        )
        logger.info(
            "Dev seed admin: user reset applied",
            extra={"email": spec.email, "role": str(spec.role)},
        )
        return

    logger.info("Dev seed admin: user exists; skipping", extra={"email": spec.email})
