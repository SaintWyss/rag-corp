"""
Name: Dev Seed Demo (Local-only)

Responsibilities:
  - Provision a local demo environment (admin + employees + workspaces)
  - Enforce safety guard: only allowed in local environment
  - Keep operations idempotent (safe to run multiple times)

Architecture:
  - Clean Architecture / Hexagonal
  - Layer: Application task (but should be wired by Infrastructure/composition root)
  - Depends on abstractions (repos/ports), not concrete Postgres implementations

Patterns:
  - Use-case/task orchestration (seed task)
  - Dependency Injection (repos + hasher injected)
  - Fail-fast guard (safety boundary)
  - Idempotent provisioning (ensure-* functions)

SOLID:
  - SRP: orchestration only; helpers split user/workspace creation
  - DIP: depends on repo ports, not Postgres modules

CRC:
  Component: ensure_dev_demo
  Responsibilities:
    - Validate environment guard
    - Ensure demo users exist
    - Ensure each user has a default workspace
  Collaborators:
    - user_repo (get_by_email/create)
    - workspace_repo (list_by_owner/create)
    - password_hasher
    - Settings (dev_seed_demo/app_env)
  Constraints:
    - Must NEVER run outside local environment
    - Must be idempotent
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import UUID

from ..crosscutting.config import Settings
from ..crosscutting.logger import logger
from ..domain.entities import Workspace, WorkspaceVisibility
from ..identity.users import UserRole

# -----------------------------
# Ports (duck-typed protocols)
# -----------------------------


class UserRecord(Protocol):
    """R: Minimal user shape required by this seed task."""

    id: UUID


class UserPort(Protocol):
    """R: User repository port needed by the seed task."""

    def get_user_by_email(self, email: str) -> UserRecord | None: ...

    def create_user(
        self, *, email: str, password_hash: str, role: UserRole, is_active: bool
    ) -> UserRecord: ...


class WorkspacePort(Protocol):
    """R: Workspace repository port needed by the seed task."""

    def list_workspaces(self, *, owner_user_id: UUID): ...

    def create_workspace(self, workspace: Workspace) -> None: ...


# -----------------------------
# Seed specs
# -----------------------------


@dataclass(frozen=True, slots=True)
class _SeedUserSpec:
    """R: Declarative user seed spec (no side effects)."""

    email: str
    password: str
    role: UserRole


# R: Canonical demo users (local only)
_DEMO_USERS: tuple[_SeedUserSpec, ...] = (
    _SeedUserSpec(email="admin@local", password="admin", role=UserRole.ADMIN),
    _SeedUserSpec(
        email="employee1@local", password="employee1", role=UserRole.EMPLOYEE
    ),
    _SeedUserSpec(
        email="employee2@local", password="employee2", role=UserRole.EMPLOYEE
    ),
)


def _assert_local_env(settings: Settings) -> None:
    """
    R: Safety guard: DEV_SEED_DEMO must only run in local.
    Fail-fast to prevent accidental seeding in real environments.
    """
    env = (settings.app_env or "").strip().lower()
    if env != "local":
        raise RuntimeError(
            f"FATAL: DEV_SEED_DEMO is enabled but ENV is '{env}' (must be 'local'). "
            "Safety guard prevents accidental overrides."
        )


def _default_workspace_name(email: str) -> str:
    """R: Stable naming convention for demo workspaces (idempotency)."""
    owner_label = (email.split("@", 1)[0] or "User").strip()
    return f"{owner_label.capitalize()} Workspace"


def _ensure_user(
    *,
    spec: _SeedUserSpec,
    user_repo: UserPort,
    password_hasher: Callable[[str], str],
) -> UserRecord:
    """
    R: Ensure a user exists (idempotent).

    Returns:
        User entity shape with `.id`
    """
    email = spec.email
    role = spec.role

    user = user_repo.get_user_by_email(email)
    if user:
        logger.info(
            "Dev seed demo: user already exists",
            extra={"email": email, "role": str(role)},
        )
        return user

    password_hash = password_hasher(spec.password)
    user = user_repo.create_user(
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=True,
    )
    logger.info(
        "Dev seed demo: user created", extra={"email": email, "role": str(role)}
    )
    return user


def _ensure_workspace(
    *,
    owner_user_id: UUID,
    owner_email: str,
    workspace_repo: WorkspacePort,
    visibility: WorkspaceVisibility = WorkspaceVisibility.PRIVATE,
) -> None:
    """
    R: Ensure the default workspace exists for the given owner (idempotent).

    Nota:
      - Hoy usamos list_workspaces + scan in-memory por simplicidad (seed local).
      - Senior upgrade futuro: repo.get_by_owner_and_name(owner_id, name).
    """
    ws_name = _default_workspace_name(owner_email)

    existing = workspace_repo.list_workspaces(owner_user_id=owner_user_id)
    if any(getattr(ws, "name", None) == ws_name for ws in existing):
        logger.info(
            "Dev seed demo: workspace already exists",
            extra={"owner_email": owner_email, "workspace_name": ws_name},
        )
        return

    workspace_repo.create_workspace(
        Workspace(
            name=ws_name,
            owner_user_id=owner_user_id,
            visibility=visibility,
        )
    )
    logger.info(
        "Dev seed demo: workspace created",
        extra={
            "owner_email": owner_email,
            "workspace_name": ws_name,
            "visibility": str(visibility),
        },
    )


def ensure_dev_demo(
    settings: Settings,
    *,
    user_repo: UserPort,
    workspace_repo: WorkspacePort,
    password_hasher: Callable[[str], str],
) -> None:
    """
    R: Ensure demo environment exists if configured.

    Creates (local only):
      - Admin user (admin@local / admin)
      - Employee users (employee1@local, employee2@local)
      - A default private workspace per user

    Fail-fast:
      - If dev_seed_demo is enabled but env != local
    """
    if not settings.dev_seed_demo:
        return

    _assert_local_env(settings)

    logger.info("Dev seed demo: starting provisioning")

    for spec in _DEMO_USERS:
        user = _ensure_user(
            spec=spec, user_repo=user_repo, password_hasher=password_hasher
        )
        _ensure_workspace(
            owner_user_id=user.id,
            owner_email=spec.email,
            workspace_repo=workspace_repo,
            visibility=WorkspaceVisibility.PRIVATE,
        )

    logger.info("Dev seed demo: provisioning complete")
