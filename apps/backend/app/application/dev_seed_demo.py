# =============================================================================
# FILE: application/dev_seed_demo.py
# =============================================================================
"""
===============================================================================
TASK: Dev Seed Demo (Local-only)
===============================================================================

Name:
    Dev Seed Demo (Local-only)

Qué es:
    Provisiona un entorno demo local:
      - usuarios (admin + empleados)
      - un workspace privado por usuario

Seguridad:
    - Guard estricto: solo corre en app_env == "local"

Patrones:
    - Task orchestration (seed)
    - Dependency Injection (repos + hasher)
    - Idempotencia (safe para ejecutar múltiples veces)

SOLID:
    - SRP: orquestación de seeding demo y helpers específicos
    - DIP: depende de puertos (protocols), no de infra concreta

CRC:
    Component: ensure_dev_demo
    Responsibilities:
      - Validar guard de ambiente
      - Asegurar usuarios demo
      - Asegurar workspace default por usuario
    Collaborators:
      - user_repo (get_by_email/create)
      - workspace_repo (list_by_owner/create)
      - password_hasher
      - Settings
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final, Protocol
from uuid import UUID, uuid4

from ..crosscutting.config import Settings
from ..crosscutting.logger import logger
from ..domain.entities import Workspace, WorkspaceVisibility
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


class WorkspaceRecord(Protocol):
    """Minimal workspace shape needed for idempotency checks."""

    name: str


class WorkspacePort(Protocol):
    """Workspace repository port needed by the seed task."""

    def list_workspaces(self, *, owner_user_id: UUID): ...

    def create_workspace(self, workspace: Workspace) -> None: ...


# -----------------------------------------------------------------------------
# Seed specs
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class _SeedUserSpec:
    """Declarative user seed spec (no side effects)."""

    email: str
    password: str
    role: UserRole


_DEMO_USERS: Final[tuple[_SeedUserSpec, ...]] = (
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
    Safety guard: DEV_SEED_DEMO must only run in local.
    Fail-fast to prevent accidental seeding in real environments.
    """
    env = (settings.app_env or "").strip().lower()
    if env != "local":
        raise RuntimeError(
            f"FATAL: DEV_SEED_DEMO is enabled but ENV is '{env}' (must be 'local'). "
            "Safety guard prevents accidental overrides."
        )


def _default_workspace_name(email: str) -> str:
    """Stable naming convention for demo workspaces (idempotency)."""
    owner_label = (email.split("@", 1)[0] or "User").strip()
    return f"{owner_label.capitalize()} Workspace"


def _ensure_user(
    *,
    spec: _SeedUserSpec,
    user_repo: UserPort,
    password_hasher: Callable[[str], str],
) -> UserRecord:
    """
    Ensure a user exists (idempotent).

    Returns:
        User entity shape with `.id`
    """
    user = user_repo.get_user_by_email(spec.email)
    if user:
        logger.info(
            "Dev seed demo: user already exists",
            extra={"email": spec.email, "role": str(spec.role)},
        )
        return user

    password_hash = password_hasher(spec.password)
    created = user_repo.create_user(
        email=spec.email,
        password_hash=password_hash,
        role=spec.role,
        is_active=True,
    )
    logger.info(
        "Dev seed demo: user created",
        extra={"email": spec.email, "role": str(spec.role)},
    )
    return created


def _ensure_workspace(
    *,
    owner_user_id: UUID,
    owner_email: str,
    workspace_repo: WorkspacePort,
    visibility: WorkspaceVisibility = WorkspaceVisibility.PRIVATE,
) -> None:
    """
    Ensure the default workspace exists for the given owner (idempotent).

    Nota:
        - Para seed local, hacemos list + scan por nombre.
        - No se asume existencia de un método repo específico.
    """
    ws_name = _default_workspace_name(owner_email)

    existing = workspace_repo.list_workspaces(owner_user_id=owner_user_id)
    if any(getattr(ws, "name", None) == ws_name for ws in existing):
        logger.info(
            "Dev seed demo: workspace already exists",
            extra={"owner_email": owner_email, "workspace_name": ws_name},
        )
        return

    # Nota: Workspace suele requerir id en el dominio; lo generamos aquí.
    workspace_repo.create_workspace(
        Workspace(
            id=uuid4(),
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
    Ensure demo environment exists if configured.

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
