"""
Name: PostgreSQL User Repository

Responsibilities:
  - Load users for authentication by email or ID
  - Map database rows into User records
"""

from typing import Optional, List
from uuid import UUID, uuid4

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


def list_users() -> List[User]:
    """R: Fetch all users for admin management."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, email, password_hash, role, is_active, created_at
                FROM users
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [_row_to_user(row) for row in rows]
    except Exception as e:
        logger.error(f"PostgresUserRepository: List users failed: {e}")
        raise DatabaseError(f"User listing failed: {e}")


def create_user(
    *, email: str, password_hash: str, role: UserRole, is_active: bool = True
) -> User:
    """R: Create a new user and return the record."""
    try:
        pool = _get_pool()
        user_id = uuid4()
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, password_hash, role, is_active, created_at
                """,
                (user_id, email, password_hash, role.value, is_active),
            ).fetchone()

        if not row:
            raise DatabaseError("User creation failed: no row returned")
        return _row_to_user(row)
    except Exception as e:
        logger.error(f"PostgresUserRepository: Create user failed: {e}")
        raise DatabaseError(f"User creation failed: {e}")


def set_user_active(user_id: UUID, is_active: bool) -> Optional[User]:
    """R: Enable or disable a user by ID."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE id = %s
                RETURNING id, email, password_hash, role, is_active, created_at
                """,
                (is_active, user_id),
            ).fetchone()

        if not row:
            return None
        return _row_to_user(row)
    except Exception as e:
        logger.error(f"PostgresUserRepository: Update active failed: {e}")
        raise DatabaseError(f"User update failed: {e}")


def update_user_password(user_id: UUID, password_hash: str) -> Optional[User]:
    """R: Update a user's password hash."""
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
                RETURNING id, email, password_hash, role, is_active, created_at
                """,
                (password_hash, user_id),
            ).fetchone()

        if not row:
            return None
        return _row_to_user(row)
    except Exception as e:
        logger.error(f"PostgresUserRepository: Update password failed: {e}")
        raise DatabaseError(f"User password update failed: {e}")
