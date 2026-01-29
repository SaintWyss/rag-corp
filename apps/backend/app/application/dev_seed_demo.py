"""
Name: Dev Seed Demo
Description: Logic to seed a full demo environment (admin + employees + workspaces).
"""

from ..crosscutting.config import Settings
from ..crosscutting.logger import logger
from ..domain.entities import Workspace, WorkspaceVisibility
from ..identity.auth_users import hash_password
from ..identity.users import UserRole
from ..infrastructure.repositories.postgres_user_repo import (
    create_user,
    get_user_by_email,
)
from ..infrastructure.repositories.postgres_workspace_repo import (
    PostgresWorkspaceRepository,
)


def ensure_dev_demo(settings: Settings) -> None:
    """
    R: Ensure demo environment exists if configured.
    FAIL-FAST if enabled in non-local environments.

    Creates:
    - Admin user (admin@local / admin)
    - Employee 1 (employee1@local / employee1)
    - Employee 2 (employee2@local / employee2)
    - Workspaces for each user
    """
    if not settings.dev_seed_demo:
        return

    # Guard: Fail fast in non-local environments
    current_env = settings.app_env.strip().lower()
    if current_env != "local":
        raise RuntimeError(
            f"FATAL: DEV_SEED_DEMO is enabled but ENV is '{current_env}' (must be 'local'). "
            "This is a safety guard to prevent accidental overrides."
        )

    logger.info("Dev seed demo: Starting provisioning...")

    workspace_repo = PostgresWorkspaceRepository()

    # 1. Define Users
    users_to_seed = [
        {"email": "admin@local", "pass": "admin", "role": UserRole.ADMIN},
        {"email": "employee1@local", "pass": "employee1", "role": UserRole.EMPLOYEE},
        {"email": "employee2@local", "pass": "employee2", "role": UserRole.EMPLOYEE},
    ]

    for u in users_to_seed:
        email = u["email"]
        role = u["role"]

        user = get_user_by_email(email)
        if not user:
            hashed = hash_password(u["pass"])
            user = create_user(
                email=email,
                password_hash=hashed,
                role=role,
                is_active=True,
            )
            logger.info(f"Dev seed demo: Created user {email} ({role})")
        else:
            logger.info(f"Dev seed demo: User {email} already exists")

        # 2. Ensure each user has at least one workspace
        # We check by name convention logic to be idempotent
        ws_name = f"{email.split('@')[0].capitalize()} Workspace"

        # Check if workspace exists for this owner with this name
        # Since repo doesn't have exact "get by owner and name", we can list by owner
        # and check in memory (safe for small local seed)
        user_workspaces = workspace_repo.list_workspaces(owner_user_id=user.id)
        existing_ws = next((ws for ws in user_workspaces if ws.name == ws_name), None)

        if not existing_ws:
            new_ws = Workspace(
                name=ws_name,
                owner_user_id=user.id,
                visibility=WorkspaceVisibility.PRIVATE,
            )
            workspace_repo.create_workspace(new_ws)
            logger.info(f"Dev seed demo: Created workspace '{ws_name}' for {email}")
        else:
            logger.info(
                f"Dev seed demo: Workspace '{ws_name}' already exists for {email}"
            )

    logger.info("Dev seed demo: Provisioning complete.")
