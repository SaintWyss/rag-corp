# =============================================================================
# FILE: application/dev_seed_admin.py
# =============================================================================
"""
===============================================================================
TASK: Dev Seed Admin (Local-only + E2E override)
===============================================================================

Name:
    Dev Seed Admin (Local-only + E2E override)

Qué es:
    Asegura que exista un usuario admin para desarrollo cuando está configurado.
    Soporta override en E2E para CI (sin depender de app_env == "local").

Seguridad:
    - Guard estricto: si NO es E2E => solo corre en app_env == "local".
    - Si es E2E => permite otros envs porque CI puede setear app_env distinto.

Patrones:
    - Task orchestration (seed)
    - Dependency Injection (repo + hasher + env mapping)
    - Fail-fast guard (safety boundary)
    - Idempotencia (ensure-create / optional reset)

SOLID:
    - SRP: solo lógica de seeding de admin
    - DIP: depende de puertos (protocols), no de repos concretos

CRC:
    Component: ensure_dev_admin
    Responsibilities:
      - Validar guard de ambiente
      - Resolver spec (settings vs E2E env)
      - Asegurar usuario (create o update si force_reset)
    Collaborators:
      - user_repo
      - password_hasher
      - Settings + env mapping
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final, Mapping, Protocol
from uuid import UUID

from ..crosscutting.config import Settings
from ..crosscutting.logger import logger
from ..identity.users import UserRole


# -----------------------------------------------------------------------------
# Ports (duck-typed protocols)
# -----------------------------------------------------------------------------
class UserRecord(Protocol):
    """Minimal user shape required by this seed task."""

    id: UUID


class UserPort(Protocol):
    """User repository port needed by the seed task."""

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


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_ENV_FLAG_E2E_SEED_ADMIN: Final[str] = "E2E_SEED_ADMIN"
_ENV_E2E_ADMIN_EMAIL: Final[str] = "E2E_ADMIN_EMAIL"
_ENV_E2E_ADMIN_PASSWORD: Final[str] = "E2E_ADMIN_PASSWORD"

_DEFAULT_E2E_EMAIL: Final[str] = "admin@local"
_DEFAULT_E2E_PASSWORD: Final[str] = "admin"


@dataclass(frozen=True, slots=True)
class _AdminSeedSpec:
    """Resolved seed configuration (no I/O)."""

    enabled: bool
    is_e2e: bool
    email: str
    password: str
    role: UserRole
    force_reset: bool


def _parse_bool(value: str | None) -> bool:
    """Parse common boolean env representations."""
    v = (value or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _resolve_role(role_str: str) -> UserRole:
    """Resolve UserRole with safe fallback."""
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
    Resolve seed inputs from:
      - settings (dev_seed_admin*)
      - OR E2E env override (E2E_SEED_ADMIN=true)
    """
    is_e2e = _parse_bool(env.get(_ENV_FLAG_E2E_SEED_ADMIN))

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
        email = env.get(_ENV_E2E_ADMIN_EMAIL, _DEFAULT_E2E_EMAIL)
        password = env.get(_ENV_E2E_ADMIN_PASSWORD, _DEFAULT_E2E_PASSWORD)
        role = UserRole.ADMIN  # determinismo en CI
        force_reset = False
    else:
        email = (settings.dev_seed_admin_email or "").strip()
        password = settings.dev_seed_admin_password or ""
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
    Safety guard:
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
    Ensure a development admin user exists if configured.

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

    if not spec.email or not spec.password:
        raise ValueError("Dev seed admin is enabled but email/password are empty")

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
