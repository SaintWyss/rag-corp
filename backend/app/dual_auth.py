"""
Name: Dual Auth (JWT + API Key) Authorization Helpers

Responsibilities:
  - Provide a unified Principal for JWT users and API key services
  - Allow endpoints to accept JWT or X-API-Key without breaking RBAC
  - Provide role-based gates for JWT while preserving API key permissions
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Set
from uuid import UUID

from fastapi import Header, Request

from . import auth
from .auth_users import extract_access_token, get_current_user
from .error_responses import forbidden
from .rbac import Permission, SCOPE_PERMISSIONS, get_rbac_config, require_permissions
from .users import UserRole


class PrincipalType(str, Enum):
    """R: Supported principal types."""

    USER = "user"
    SERVICE = "service"


@dataclass(frozen=True)
class UserPrincipal:
    """R: JWT-backed principal."""

    user_id: UUID
    email: str
    role: UserRole


@dataclass(frozen=True)
class ServicePrincipal:
    """R: API key-backed principal."""

    api_key_hash: str
    permissions: Set[Permission]
    rbac_role: Optional[str] = None


@dataclass(frozen=True)
class Principal:
    """R: Unified principal wrapper."""

    principal_type: PrincipalType
    user: Optional[UserPrincipal] = None
    service: Optional[ServicePrincipal] = None


def _permissions_from_scopes(scopes: Set[str]) -> Set[Permission]:
    permissions: Set[Permission] = set()
    if "*" in scopes:
        return {Permission.ALL}
    for scope in scopes:
        permissions |= SCOPE_PERMISSIONS.get(scope, set())
    return permissions


def _build_service_principal(
    *,
    api_key: str,
    key_hash: str,
    keys_config: dict[str, list[str]],
) -> ServicePrincipal:
    rbac_config = get_rbac_config()
    if rbac_config:
        role = rbac_config.get_role_for_key(key_hash)
        permissions = set(role.permissions) if role else set()
        role_name = role.name if role else None
        return ServicePrincipal(
            api_key_hash=key_hash,
            permissions=permissions,
            rbac_role=role_name,
        )

    validator = auth.APIKeyValidator(keys_config) if keys_config else None
    scopes = set(validator.get_scopes(api_key)) if validator else set()
    permissions = _permissions_from_scopes(scopes)
    return ServicePrincipal(
        api_key_hash=key_hash,
        permissions=permissions,
        rbac_role=None,
    )


def require_principal(*permissions: Permission) -> Callable:
    """
    R: Require either a JWT user or an API key service principal.

    - JWT path: validates access token and returns user principal.
    - API key path: preserves existing RBAC/permission checks.
    """

    async def dependency(
        request: Request,
        authorization: str | None = Header(None, alias="Authorization"),
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> Principal | None:
        token = extract_access_token(request, authorization)
        if token:
            user = get_current_user(token)
            principal = Principal(
                principal_type=PrincipalType.USER,
                user=UserPrincipal(
                    user_id=user.id,
                    email=user.email,
                    role=user.role,
                ),
            )
            request.state.principal = principal
            return principal

        keys_config = auth.get_keys_config()
        rbac_config = get_rbac_config()
        if not keys_config and not rbac_config:
            return None

        await require_permissions(*permissions)(request, api_key)

        if not api_key:
            return None

        key_hash = getattr(request.state, "api_key_hash", None)
        if not key_hash:
            key_hash = auth._hash_key(api_key)

        principal = Principal(
            principal_type=PrincipalType.SERVICE,
            service=_build_service_principal(
                api_key=api_key,
                key_hash=key_hash,
                keys_config=keys_config,
            ),
        )
        request.state.principal = principal
        return principal

    dependency._required_permissions = tuple(perm.value for perm in permissions)
    return dependency


def require_roles(*roles: UserRole) -> Callable:
    """R: Require one of the JWT roles (ignored for API key principals)."""
    allowed = {UserRole(role) for role in roles}

    async def dependency(request: Request) -> None:
        principal: Principal | None = getattr(request.state, "principal", None)
        if not principal or principal.principal_type == PrincipalType.SERVICE:
            return None

        if not principal.user or principal.user.role not in allowed:
            raise forbidden("Insufficient role.")

        return None

    return dependency


def require_admin() -> Callable:
    """R: Require JWT admin role."""
    return require_roles(UserRole.ADMIN)


def require_employee_or_admin() -> Callable:
    """R: Require JWT employee or admin role."""
    return require_roles(UserRole.EMPLOYEE, UserRole.ADMIN)
