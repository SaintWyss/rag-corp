"""
Name: User Authentication (JWT)

Responsibilities:
  - Verify passwords using Argon2
  - Issue and validate JWT access tokens
  - Provide FastAPI dependencies for user/role checks
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Header, Request

from .config import get_settings
from .error_responses import forbidden, unauthorized
from .logger import logger
from .users import User, UserRole
from .infrastructure.repositories.postgres_user_repo import (
    get_user_by_email,
    get_user_by_id,
)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_COOKIE = "access_token"

_password_hasher = PasswordHasher()


@dataclass(frozen=True)
class AuthSettings:
    jwt_secret: str
    jwt_access_ttl_minutes: int
    jwt_cookie_name: str
    jwt_cookie_secure: bool


@dataclass(frozen=True)
class TokenPayload:
    user_id: str
    email: str
    role: UserRole


def get_auth_settings() -> AuthSettings:
    settings = get_settings()
    return AuthSettings(
        jwt_secret=settings.jwt_secret,
        jwt_access_ttl_minutes=settings.jwt_access_ttl_minutes,
        jwt_cookie_name=settings.jwt_cookie_name,
        jwt_cookie_secure=settings.jwt_cookie_secure,
    )


def hash_password(password: str) -> str:
    """R: Hash a password using Argon2."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """R: Verify password against stored hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def authenticate_user(email: str, password: str) -> User | None:
    """R: Validate credentials and return active user."""
    normalized_email = email.strip().lower()
    user = get_user_by_email(normalized_email)
    if not user:
        return None
    if not user.is_active:
        logger.warning("Auth failed: inactive user", extra={"email": normalized_email})
        raise forbidden("User is inactive.")
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(
    user: User, settings: AuthSettings | None = None
) -> tuple[str, int]:
    """R: Create a signed JWT access token."""
    auth_settings = settings or get_auth_settings()
    now = datetime.now(timezone.utc)
    expires_in = auth_settings.jwt_access_ttl_minutes * 60
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, auth_settings.jwt_secret, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(
    token: str, settings: AuthSettings | None = None
) -> TokenPayload:
    """R: Decode and validate a JWT access token."""
    auth_settings = settings or get_auth_settings()
    try:
        payload = jwt.decode(
            token,
            auth_settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise unauthorized("Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthorized("Invalid token.") from exc

    user_id = payload.get("sub")
    email = payload.get("email")
    role_value = payload.get("role")
    if not user_id or not email or not role_value:
        raise unauthorized("Invalid token.")

    try:
        role = UserRole(role_value)
    except ValueError as exc:
        raise unauthorized("Invalid token.") from exc

    return TokenPayload(user_id=user_id, email=email, role=role)


def get_current_user(token: str) -> User:
    """R: Resolve the current user from a JWT access token."""
    payload = decode_access_token(token)
    try:
        user_id = UUID(payload.user_id)
    except ValueError as exc:
        raise unauthorized("Invalid token.") from exc

    user = get_user_by_id(user_id)
    if not user:
        raise unauthorized("Invalid token.")
    if not user.is_active:
        raise forbidden("User is inactive.")
    return user


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def extract_access_token(request: Request, authorization: str | None) -> str | None:
    """R: Resolve access token from Authorization header or cookie."""
    token = _extract_bearer_token(authorization)
    if token:
        return token
    cookie_name = get_auth_settings().jwt_cookie_name or ACCESS_TOKEN_COOKIE
    return request.cookies.get(cookie_name)


def require_user() -> Callable:
    """R: FastAPI dependency that requires a valid JWT user."""

    async def dependency(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> User:
        token = extract_access_token(request, authorization)
        if not token:
            raise unauthorized("Missing bearer token.")

        user = get_current_user(token)
        request.state.user = user
        return user

    return dependency


def require_role(role: UserRole | str) -> Callable:
    """R: FastAPI dependency that requires a specific user role."""
    required_role = UserRole(role)

    async def dependency(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> User:
        user = await require_user()(request, authorization)
        if user.role != required_role:
            raise forbidden("Insufficient role.")
        return user

    return dependency
