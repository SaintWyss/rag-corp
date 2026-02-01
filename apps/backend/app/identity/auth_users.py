"""
===============================================================================
TARJETA CRC — identity/auth_users.py
===============================================================================

Módulo:
    Autenticación de Usuarios (JWT)

Responsabilidades:
    - Hashear/verificar passwords (Argon2).
    - Emitir JWT de acceso con expiración (access token).
    - Decodificar y validar JWT (firma, exp, claims mínimos).
    - Resolver usuario actual (token -> user_id -> repo).
    - Exponer dependencias FastAPI (require_user, require_role).
    - Extraer token desde Authorization: Bearer o cookie.

Colaboradores:
    - crosscutting.config.get_settings: secretos, TTL, cookie settings.
    - crosscutting.error_responses: unauthorized/forbidden estándar.
    - crosscutting.logger: logging estructurado.
    - infrastructure.repositories.postgres.user: get_user_by_email/get_user_by_id.
    - identity.users: User / UserRole.

Decisiones de diseño (Senior / Clean Architecture):
    - La lógica criptográfica vive acá (borde de identidad), NO en dominio.
    - El módulo expone helpers puros y dependencias FastAPI separadas.
    - Claims mínimos: sub, email, role, exp, iat.
    - No loguear secretos ni tokens; solo info mínima y segura.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Header, Request

from ..crosscutting.config import get_settings
from ..crosscutting.error_responses import forbidden, unauthorized
from ..crosscutting.logger import logger
from ..infrastructure.repositories.postgres.user import (
    get_user_by_email,
    get_user_by_id,
)
from .users import User, UserRole

# ---------------------------------------------------------------------------
# Constantes (evitan strings mágicos)
# ---------------------------------------------------------------------------

JWT_ALGORITHM: str = "HS256"

# R: fallback si Settings no define cookie.
DEFAULT_ACCESS_TOKEN_COOKIE: str = "access_token"

# R: claims. (Compatibles con muchos middlewares estándar)
CLAIM_SUB: str = "sub"
CLAIM_EMAIL: str = "email"
CLAIM_ROLE: str = "role"
CLAIM_IAT: str = "iat"
CLAIM_EXP: str = "exp"
CLAIM_TYP: str = "typ"

TOKEN_TYPE_ACCESS: str = "access"

_password_hasher = PasswordHasher()


# ---------------------------------------------------------------------------
# Contratos internos
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Settings de auth (snapshot)."""

    jwt_secret: str
    jwt_access_ttl_minutes: int
    jwt_cookie_name: str
    jwt_cookie_secure: bool


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Payload mínimo que esperamos de un access token."""

    user_id: str
    email: str
    role: UserRole


def get_auth_settings() -> AuthSettings:
    """Construye un snapshot de settings de auth."""
    s = get_settings()
    return AuthSettings(
        jwt_secret=s.jwt_secret,
        jwt_access_ttl_minutes=s.jwt_access_ttl_minutes,
        jwt_cookie_name=s.jwt_cookie_name,
        jwt_cookie_secure=s.jwt_cookie_secure,
    )


# ---------------------------------------------------------------------------
# Passwords (Argon2)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hashea un password usando Argon2."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica password vs hash almacenado."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def authenticate_user(email: str, password: str) -> User | None:
    """Valida credenciales y retorna el usuario activo o None.

    Seguridad:
        - Normalizamos el email (trim/lower) en el borde de identidad.
        - No diferenciamos “usuario no existe” vs “password incorrecto” (retorna None).
        - Si el usuario existe pero está inactivo, devolvemos 403 para dejarlo explícito.
    """
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return None

    user = get_user_by_email(normalized_email)
    if not user:
        return None

    if not user.is_active:
        logger.warning(
            "Auth falló: usuario inactivo", extra={"email": normalized_email}
        )
        raise forbidden("El usuario está inactivo.")

    if not verify_password(password, user.password_hash):
        return None

    return user


# ---------------------------------------------------------------------------
# Tokens JWT (emitir / decodificar)
# ---------------------------------------------------------------------------


def create_access_token(
    user: User, settings: AuthSettings | None = None
) -> tuple[str, int]:
    """Crea un JWT de acceso (access token) firmado.

    Retorna:
        (token, expires_in_seconds)
    """
    auth_settings = settings or get_auth_settings()

    now = datetime.now(timezone.utc)
    expires_in = int(auth_settings.jwt_access_ttl_minutes * 60)

    payload: dict[str, object] = {
        CLAIM_SUB: str(user.id),
        CLAIM_EMAIL: user.email,
        CLAIM_ROLE: user.role.value,
        CLAIM_IAT: int(now.timestamp()),
        CLAIM_EXP: int((now + timedelta(seconds=expires_in)).timestamp()),
        CLAIM_TYP: TOKEN_TYPE_ACCESS,
    }

    token = jwt.encode(payload, auth_settings.jwt_secret, algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(
    token: str, settings: AuthSettings | None = None
) -> TokenPayload:
    """Decodifica y valida un JWT de acceso.

    Errores:
        - 401 si expiró o firma inválida.
        - 401 si faltan claims mínimos.
    """
    auth_settings = settings or get_auth_settings()

    try:
        payload = jwt.decode(
            token,
            auth_settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": [CLAIM_SUB, CLAIM_EMAIL, CLAIM_ROLE, CLAIM_EXP],
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise unauthorized("Token expirado.") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthorized("Token inválido.") from exc

    user_id = payload.get(CLAIM_SUB)
    email = payload.get(CLAIM_EMAIL)
    role_value = payload.get(CLAIM_ROLE)
    token_type = payload.get(CLAIM_TYP)

    if not user_id or not email or not role_value:
        raise unauthorized("Token inválido.")

    # R: si viene typ, lo validamos; si no viene, lo aceptamos por compatibilidad.
    if token_type is not None and token_type != TOKEN_TYPE_ACCESS:
        raise unauthorized("Tipo de token inválido.")

    try:
        role = UserRole(str(role_value))
    except ValueError as exc:
        raise unauthorized("Token inválido.") from exc

    return TokenPayload(user_id=str(user_id), email=str(email), role=role)


def get_current_user(token: str) -> User:
    """Resuelve el usuario actual a partir del access token."""
    payload = decode_access_token(token)

    try:
        user_id = UUID(payload.user_id)
    except ValueError as exc:
        raise unauthorized("Token inválido.") from exc

    user = get_user_by_id(user_id)
    if not user:
        raise unauthorized("Token inválido.")
    if not user.is_active:
        raise forbidden("El usuario está inactivo.")
    return user


# ---------------------------------------------------------------------------
# Extracción de token (header/cookie)
# ---------------------------------------------------------------------------


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Extrae token desde `Authorization: Bearer <token>`."""
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def extract_access_token(request: Request, authorization: str | None) -> str | None:
    """Resuelve token desde Authorization o cookie."""
    token = _extract_bearer_token(authorization)
    if token:
        return token

    cookie_name = (
        get_auth_settings().jwt_cookie_name or ""
    ).strip() or DEFAULT_ACCESS_TOKEN_COOKIE
    return request.cookies.get(cookie_name)


# ---------------------------------------------------------------------------
# Dependencias FastAPI
# ---------------------------------------------------------------------------


def require_user() -> Callable:
    """Dependency FastAPI: requiere usuario autenticado por JWT."""

    async def dependency(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> User:
        token = extract_access_token(request, authorization)
        if not token:
            raise unauthorized("Falta token Bearer.")

        user = get_current_user(token)
        request.state.user = user
        return user

    return dependency


def require_role(role: UserRole | str) -> Callable:
    """Dependency FastAPI: requiere un rol específico de usuario."""
    required_role = UserRole(role)

    async def dependency(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> User:
        user = await require_user()(request, authorization)
        if user.role != required_role:
            raise forbidden("Rol insuficiente.")
        return user

    return dependency
