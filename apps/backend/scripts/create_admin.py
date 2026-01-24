"""
Name: Admin Bootstrap Script

Responsibilities:
  - Create the first admin user (idempotent)
  - Hash passwords with Argon2
  - Store user in PostgreSQL
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from uuid import uuid4

import psycopg

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.auth_users import hash_password  # noqa: E402
from app.users import UserRole  # noqa: E402


def _require_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL is required to create a user.")
    return db_url


def _prompt_email() -> str:
    email = input("Email: ").strip().lower()
    if not email:
        raise SystemExit("Email is required.")
    return email


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    if not password:
        raise SystemExit("Password is required.")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    return password


def _parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    parser = argparse.ArgumentParser(
        description="Create the first admin user (idempotent)."
    )
    parser.add_argument("--email", help="User email (will be normalized)")
    parser.add_argument(
        "--password",
        help="User password (omit to be prompted securely)",
    )
    parser.add_argument(
        "--role",
        default=UserRole.ADMIN.value,
        choices=[role.value for role in UserRole],
        help="User role (default: admin)",
    )
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create user as inactive",
    )
    return parser.parse_args(argv)


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise SystemExit("Email is required.")
    return normalized


def _maybe_create_user(db_url: str, email: str, password: str, role: str, active: bool):
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, role, is_active FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
            if row:
                print(
                    "User already exists: "
                    f"id={row[0]} email={email} role={row[1]} active={row[2]}"
                )
                return

            user_id = uuid4()
            password_hash = hash_password(password)
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, email, password_hash, role, active),
            )
            conn.commit()
            print(f"Created user: id={user_id} email={email} role={role}")


def main() -> None:
    args = _parse_args()
    db_url = _require_database_url()
    email = _normalize_email(args.email) if args.email else _prompt_email()
    password = args.password or _prompt_password()
    _maybe_create_user(
        db_url,
        email=email,
        password=password,
        role=args.role,
        active=not args.inactive,
    )


if __name__ == "__main__":
    main()
