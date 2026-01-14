"""
Name: PostgreSQL User Repository

Responsibilities:
  - Load users for authentication by email or ID
  - Map database rows into User records
"""

from typing import Optional
from uuid import UUID

from psycopg_pool import ConnectionPool

from ...exceptions import DatabaseError
from ...logger import logger
from ...users import User, UserRole


def _get_pool() -> ConnectionPool:
    from ..db.pool import get_pool

    return get_pool()


def _row_to_user(row) -> User:
    try:
        role = UserRole(row[3])
    except ValueError as exc:
        raise DatabaseError(f"Invalid user role in database: {row[3]}") from exc

    return User(
        id=row[0],
        email=row[1],
        password_hash=row[2],
        role=role,
        is_active=row[4],
        created_at=row[5],
    )


def get_user_by_email(email: str) -> Optional[User]:
    """R: Fetch user by email for authentication."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, password_hash, role, is_active, created_at
                FROM users
                WHERE email = %s
                """,
                (email,),
            ).fetchone()

        if not row:
            return None
        return _row_to_user(row)
    except Exception as e:
        logger.error(f"PostgresUserRepository: Get by email failed: {e}")
        raise DatabaseError(f"User lookup failed: {e}")


def get_user_by_id(user_id: UUID) -> Optional[User]:
    """R: Fetch user by ID for access token validation."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, password_hash, role, is_active, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()

        if not row:
            return None
        return _row_to_user(row)
    except Exception as e:
        logger.error(f"PostgresUserRepository: Get by id failed: {e}")
        raise DatabaseError(f"User lookup failed: {e}")
