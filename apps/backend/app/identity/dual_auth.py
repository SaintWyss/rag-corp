"""
===============================================================================
TARJETA CRC — identity/dual_auth.py
===============================================================================

Módulo:
    Dual Auth (JWT + API Key) — Principal Unificado

Responsabilidades:
    - Construir un Principal unificado para:
        (a) usuario autenticado por JWT
        (b) servicio autenticado por API key (con RBAC/permisos)
    - Resolver credenciales desde headers/cookies (JWT) o headers (API key).
    - Enforzar permisos (API keys) con require_permissions (RBAC/scope fallback).
    - Exponer dependencias FastAPI para:
        - require_principal (user o service)
        - require_roles (solo usuarios, API keys se ignoran)
        - require_user_roles (solo usuarios, API keys se rechazan)

Colaboradores:
    - identity.auth_users: extracción y validación de token JWT.
    - identity.auth: lectura de API_KEYS_CONFIG y hashing seguro.
    - identity.rbac: permisos, RBAC_CONFIG y dependencia require_permissions.
    - crosscutting.error_responses: forbidden estándar.
    - FastAPI: Request/Header para DI.

Patrones:
    - Strategy (en runtime elegimos el “camino” de auth disponible).
    - Adapter (depende de FastAPI pero expone modelos neutros/puros).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Set
from uuid import UUID

from fastapi import Header, Request

from ..crosscutting.error_responses import forbidden
from . import auth
from .auth_users import extract_access_token, get_current_user
from .rbac import SCOPE_PERMISSIONS, Permission, get_rbac_config, require_permissions
from .users import UserRole

# ---------------------------------------------------------------------------
# Modelo de Principal
# ---------------------------------------------------------------------------


class PrincipalType(str, Enum):
    """Tipos de principal soportados."""

    USER = "user"
    SERVICE = "service"


@dataclass(frozen=True, slots=True)
class UserPrincipal:
    """Principal respaldado por JWT."""

    user_id: UUID
    email: str
    role: UserRole


@dataclass(frozen=True, slots=True)
class ServicePrincipal:
    """Principal respaldado por API key."""

    api_key_hash: str
    permissions: Set[Permission]
    rbac_role: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Principal:
    """Wrapper unificado para consumir desde routes / use cases."""

    principal_type: PrincipalType
    user: Optional[UserPrincipal] = None
    service: Optional[ServicePrincipal] = None


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _permissions_from_scopes(scopes: Set[str]) -> Set[Permission]:
    """Convierte scopes a permisos usando el mapeo local."""
    if "*" in scopes:
        return {Permission.ALL}

    permissions: Set[Permission] = set()
    for scope in scopes:
        permissions |= SCOPE_PERMISSIONS.get(scope, set())
    return permissions


def _build_service_principal(
    *,
    api_key: str,
    key_hash: str,
    keys_config: dict[str, list[str]],
) -> ServicePrincipal:
    """Construye principal de servicio usando RBAC_CONFIG si existe, o scopes si no."""
    rbac_cfg = get_rbac_config()
    if rbac_cfg:
        role = rbac_cfg.get_role_for_key(key_hash)
        permissions = set(role.permissions) if role else set()
        role_name = role.name if role else None
        return ServicePrincipal(
            api_key_hash=key_hash,
            permissions=permissions,
            rbac_role=role_name,
        )

    # Fallback scopes (API_KEYS_CONFIG).
    validator = auth.APIKeyValidator(keys_config) if keys_config else None
    scopes = set(validator.get_scopes(api_key)) if validator else set()
    permissions = _permissions_from_scopes(scopes)
    return ServicePrincipal(
        api_key_hash=key_hash, permissions=permissions, rbac_role=None
    )


# ---------------------------------------------------------------------------
# Dependencias FastAPI
# ---------------------------------------------------------------------------


def require_principal(*permissions: Permission) -> Callable:
    """Dependency FastAPI: requiere principal USER o SERVICE.

    Prioridad:
        1) JWT si existe Authorization: Bearer ... o cookie.
        2) API key si está configurada (API_KEYS_CONFIG o RBAC_CONFIG).
        3) Si no hay configuración, retorna None (compatibilidad).

    Nota:
        - Para API keys, delegamos autorización en require_permissions().
        - Si pedís permisos, se validan solo para el camino de API key.
    """

    async def dependency(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> Principal | None:
        # -----------------------
        # Camino 1: JWT
        # -----------------------
        token = extract_access_token(request, authorization)
        if token:
            user = get_current_user(token)
            principal = Principal(
                principal_type=PrincipalType.USER,
                user=UserPrincipal(user_id=user.id, email=user.email, role=user.role),
            )
            request.state.principal = principal
            return principal

        # -----------------------
        # Camino 2: API key
        # -----------------------
        keys_cfg = auth.get_keys_config()
        rbac_cfg = get_rbac_config()
        if not keys_cfg and not rbac_cfg:
            # R: No hay auth configurada. Compatibilidad: dejamos pasar.
            return None

        # R: Enforce permisos (si corresponde) y valida API key si aplica.
        await require_permissions(*permissions)(request, api_key)

        if not api_key:
            return None

        # R: Preferimos request.state.api_key_hash (si require_permissions lo setea).
        key_hash = getattr(request.state, "api_key_hash", None) or auth._hash_key(
            api_key
        )

        principal = Principal(
            principal_type=PrincipalType.SERVICE,
            service=_build_service_principal(
                api_key=api_key, key_hash=key_hash, keys_config=keys_cfg
            ),
        )
        request.state.principal = principal
        return principal

    dependency._required_permissions = tuple(p.value for p in permissions)
    return dependency


def require_roles(*roles: UserRole) -> Callable:
    """Dependency FastAPI: requiere rol de usuario (API keys se ignoran)."""
    allowed = {UserRole(r) for r in roles}

    async def dependency(request: Request) -> None:
        principal: Principal | None = getattr(request.state, "principal", None)

        # R: Si no hay principal o es SERVICE, no aplicamos (compatibilidad).
        if not principal or principal.principal_type == PrincipalType.SERVICE:
            return None

        if not principal.user or principal.user.role not in allowed:
            raise forbidden("Rol insuficiente.")

        return None

    return dependency


def require_admin() -> Callable:
    return require_roles(UserRole.ADMIN)


def require_employee_or_admin() -> Callable:
    return require_roles(UserRole.EMPLOYEE, UserRole.ADMIN)


def require_user_roles(*roles: UserRole) -> Callable:
    """Dependency FastAPI: requiere JWT (usuario) con uno de los roles.

    Diferencia clave:
        - require_roles() ignora SERVICE.
        - require_user_roles() rechaza SERVICE.
    """
    allowed = {UserRole(r) for r in roles}

    async def dependency(request: Request) -> None:
        principal: Principal | None = getattr(request.state, "principal", None)

        # R: Si no hay principal (auth deshabilitada), no hacemos nada (compatibilidad).
        if not principal:
            return None

        if principal.principal_type != PrincipalType.USER or not principal.user:
            raise forbidden("Se requiere autenticación de usuario.")

        if principal.user.role not in allowed:
            raise forbidden("Rol insuficiente.")

        return None

    return dependency


def require_user_admin() -> Callable:
    return require_user_roles(UserRole.ADMIN)


def require_user_employee_or_admin() -> Callable:
    return require_user_roles(UserRole.EMPLOYEE, UserRole.ADMIN)
