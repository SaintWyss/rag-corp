"""
Name: Dev Seed Admin
Description: Logic to seed a development admin user on startup.
"""

from ..platform.config import Settings
from ..platform.logger import logger
from ..identity.auth_users import hash_password
from ..identity.users import UserRole
from ..infrastructure.repositories.postgres_user_repo import (
    get_user_by_email,
    create_user,
    update_user,
)


def ensure_dev_admin(settings: Settings) -> None:
    """
    R: Ensure a development admin user exists if configured.
    FAIL-FAST if enabled in non-local environments.
    """
    if not settings.dev_seed_admin:
        return

    # Guard: Fail fast in non-local environments
    # We check raw app_env string to be sure, or rely on is_production() logic?
    # Better to be explicit: allow only "local" or "development".
    # settings.app_env defaults to "development" in config.py.
    # We should strictly enforce "local" if the user follows runbook,
    # or just ensure it's NOT production and maybe check a specific "local" flag.
    # The prompt says: "si ENV != local y DEV_SEED_ADMIN=1, la app debe FAIL-FAST"
    
    # We will assume "local" is the value user sets for local dev.
    # Current config defaults to "development".
    # Let's check against what the user is expected to use. 
    # The prompt says "ENV=local".
    
    current_env = settings.app_env.strip().lower()
    if current_env != "local":
        raise RuntimeError(
            f"FATAL: DEV_SEED_ADMIN is enabled but ENV is '{current_env}' (must be 'local'). "
            "This is a safety guard to prevent accidental overrides."
        )

    target_email = settings.dev_seed_admin_email
    target_password = settings.dev_seed_admin_password
    target_role_str = settings.dev_seed_admin_role
    force_reset = settings.dev_seed_admin_force_reset

    try:
        target_role = UserRole(target_role_str)
    except ValueError:
        logger.warning(
            f"Dev seed admin: Invalid role '{target_role_str}', falling back to ADMIN"
        )
        target_role = UserRole.ADMIN

    logger.info(f"Dev seed admin: Ensuring user {target_email} exists...")

    existing_user = get_user_by_email(target_email)

    if not existing_user:
        # Create new
        hashed = hash_password(target_password)
        create_user(
            email=target_email,
            password_hash=hashed,
            role=target_role,
            is_active=True,
        )
        logger.info(f"Dev seed admin: Created new admin user {target_email}")
    
    elif force_reset:
        # Update existing
        hashed = hash_password(target_password)
        update_user(
            existing_user.id,
            password_hash=hashed,
            role=target_role,
            is_active=True,
        )
        logger.info(f"Dev seed admin: Reset existing user {target_email} (FORCE_RESET=1)")
    
    else:
        logger.info(f"Dev seed admin: User {target_email} already exists (skipping)")
