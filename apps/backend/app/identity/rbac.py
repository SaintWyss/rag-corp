"""
===============================================================================
TARJETA CRC — identity/rbac.py
===============================================================================

Módulo:
    RBAC (Role-Based Access Control) para API Keys

Responsabilidades:
    - Definir el catálogo de permisos (Permission).
    - Definir roles (Role) con permisos e herencia.
    - Cargar RBAC_CONFIG desde env (JSON) y construir un RBACConfig cacheado.
    - Resolver permisos para una API key (por hash).
    - Exponer dependencias FastAPI:
        - require_permissions / require_permission
        - require_metrics_permission
        - require_role (si se usa modelo por roles)

Colaboradores:
    - identity.auth: validación de API key y cálculo de hash para request.state.
    - crosscutting.logger: logs estructurados.
    - crosscutting.error_responses: unauthorized/forbidden estándar.
    - crosscutting.config: valida en producción que exista RBAC_CONFIG o API_KEYS_CONFIG.

Notas de diseño:
    - Si RBAC_CONFIG está presente, es la fuente principal de autorización para API keys.
    - Si RBAC_CONFIG no está presente pero API_KEYS_CONFIG sí, usamos un mapeo
      “scope -> permisos” para mantener compatibilidad.
    - El dominio NO debe conocer RBAC: esto vive en la frontera (identity).
===============================================================================
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Callable, Optional, Set

from fastapi import Header, Request

from ..crosscutting.error_responses import forbidden, unauthorized
from ..crosscutting.logger import logger

# ---------------------------------------------------------------------------
# Permisos (lenguaje ubicuo para autorización)
# ---------------------------------------------------------------------------


class Permission(str, Enum):
    """Permisos disponibles en el sistema."""

    # Documentos
    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_DELETE = "documents:delete"

    # Query / RAG
    QUERY_SEARCH = "query:search"
    QUERY_ASK = "query:ask"
    QUERY_STREAM = "query:stream"

    # Admin
    ADMIN_METRICS = "admin:metrics"
    ADMIN_HEALTH = "admin:health"
    ADMIN_CONFIG = "admin:config"

    # Wildcard
    ALL = "*"


# ---------------------------------------------------------------------------
# Mapeo scope -> permisos (fallback cuando NO hay RBAC_CONFIG)
# ---------------------------------------------------------------------------

SCOPE_PERMISSIONS: dict[str, Set[Permission]] = {
    "ingest": {
        Permission.DOCUMENTS_CREATE,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_DELETE,
    },
    "ask": {
        Permission.DOCUMENTS_READ,
        Permission.QUERY_SEARCH,
        Permission.QUERY_ASK,
        Permission.QUERY_STREAM,
    },
    "metrics": {Permission.ADMIN_METRICS},
}

# R: Invertimos para saber qué scopes habilitan un permiso (si se necesita).
_PERMISSION_SCOPES: dict[Permission, Set[str]] = {}
for scope, permissions in SCOPE_PERMISSIONS.items():
    for perm in permissions:
        _PERMISSION_SCOPES.setdefault(perm, set()).add(scope)


# ---------------------------------------------------------------------------
# Modelo RBAC (roles + herencia)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Role:
    """Definición de rol: permisos + herencia opcional."""

    name: str
    permissions: Set[Permission] = field(default_factory=set)
    inherits_from: Optional[str] = None
    description: str = ""

    def has_permission(
        self, permission: Permission, roles_registry: dict[str, "Role"]
    ) -> bool:
        """Verifica permiso directo o heredado."""
        if Permission.ALL in self.permissions:
            return True
        if permission in self.permissions:
            return True

        parent = self.inherits_from
        if parent and parent in roles_registry:
            return roles_registry[parent].has_permission(permission, roles_registry)

        return False


# R: roles por defecto para acelerar adopción.
DEFAULT_ROLES: dict[str, Role] = {
    "admin": Role(
        name="admin", permissions={Permission.ALL}, description="Acceso total"
    ),
    "user": Role(
        name="user",
        permissions={
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_READ,
            Permission.QUERY_SEARCH,
            Permission.QUERY_ASK,
            Permission.QUERY_STREAM,
        },
        description="Usuario estándar",
    ),
    "readonly": Role(
        name="readonly",
        permissions={
            Permission.DOCUMENTS_READ,
            Permission.QUERY_SEARCH,
            Permission.QUERY_ASK,
        },
        description="Solo lectura",
    ),
    "ingest-only": Role(
        name="ingest-only",
        permissions={Permission.DOCUMENTS_CREATE},
        description="Solo ingesta",
    ),
}


@dataclass(frozen=True, slots=True)
class RBACConfig:
    """Configuración RBAC: roles + asignación hash(API key) -> rol."""

    roles: dict[str, Role]
    key_roles: dict[str, str]  # key_hash -> role_name

    def get_role_for_key(self, key_hash: str) -> Optional[Role]:
        role_name = self.key_roles.get(key_hash)
        return self.roles.get(role_name) if role_name else None

    def check_permission(self, key_hash: str, permission: Permission) -> bool:
        role = self.get_role_for_key(key_hash)
        return bool(role and role.has_permission(permission, self.roles))


# ---------------------------------------------------------------------------
# Parsing de configuración (cacheado)
# ---------------------------------------------------------------------------


def _parse_permissions(values: object) -> Set[Permission]:
    """Parsea lista de strings a Set[Permission] de manera defensiva."""
    if not isinstance(values, list):
        return set()

    parsed: Set[Permission] = set()
    for v in values:
        if not isinstance(v, str) or not v.strip():
            continue
        try:
            parsed.add(Permission(v.strip()))
        except ValueError:
            logger.warning("Permiso RBAC desconocido", extra={"permission": v})
    return parsed


@lru_cache(maxsize=1)
def _parse_rbac_config() -> Optional[RBACConfig]:
    """Parsea RBAC_CONFIG desde env y construye RBACConfig."""
    raw = (os.getenv("RBAC_CONFIG") or "").strip()
    if not raw:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("RBAC_CONFIG inválido (JSON)", extra={"error": str(exc)})
        return None

    if not isinstance(data, dict):
        logger.warning("RBAC_CONFIG inválido (shape)")
        return None

    # 1) Roles: default + overrides.
    roles: dict[str, Role] = dict(DEFAULT_ROLES)

    custom_roles = data.get("roles", {})
    if isinstance(custom_roles, dict):
        for role_name, role_data in custom_roles.items():
            if not isinstance(role_name, str) or not role_name.strip():
                continue
            if not isinstance(role_data, dict):
                continue

            permissions = _parse_permissions(role_data.get("permissions", []))
            inherits_from = role_data.get("inherits_from")
            inherits_from = (
                inherits_from.strip()
                if isinstance(inherits_from, str) and inherits_from.strip()
                else None
            )
            description = role_data.get("description", "")
            description = description.strip() if isinstance(description, str) else ""

            roles[role_name.strip()] = Role(
                name=role_name.strip(),
                permissions=permissions,
                inherits_from=inherits_from,
                description=description,
            )

    # 2) Mapeo key_hash -> rol.
    key_roles_raw = data.get("key_roles", {})
    key_roles: dict[str, str] = {}
    if isinstance(key_roles_raw, dict):
        for k, v in key_roles_raw.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                key_roles[k.strip()] = v.strip()

    return RBACConfig(roles=roles, key_roles=key_roles)


def get_rbac_config() -> Optional[RBACConfig]:
    """Devuelve RBACConfig cacheado (o None)."""
    return _parse_rbac_config()


def clear_rbac_cache() -> None:
    """Limpia cache (tests / hot-reload local)."""
    _parse_rbac_config.cache_clear()


def is_rbac_enabled() -> bool:
    return get_rbac_config() is not None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def _required_scopes_for_permissions(perms: Set[Permission]) -> Set[str]:
    scopes: Set[str] = set()
    for p in perms:
        scopes |= _PERMISSION_SCOPES.get(p, set())
    return scopes


def require_permissions(*permissions: Permission) -> Callable:
    """Dependency FastAPI: requiere permisos para API key.

    Semántica:
        - Si pasás varios permisos, se permite si cumple **al menos uno** (OR).

    Resolución:
        - Si existe RBAC_CONFIG: se evalúa contra rol asignado al hash de la key.
        - Si no existe RBAC_CONFIG pero sí API_KEYS_CONFIG: se evalúa por scopes.

    Si no hay configuración de auth (ni RBAC ni API_KEYS): es NO-OP.
    """
    required: Set[Permission] = set(permissions)

    async def dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        from .auth import APIKeyValidator, _hash_key, get_keys_config

        keys_cfg = get_keys_config()
        rbac_cfg = get_rbac_config()

        # R: sin configuración => auth deshabilitada.
        if not keys_cfg and not rbac_cfg:
            return None

        if not api_key:
            logger.warning(
                "Auth falló: falta X-API-Key", extra={"path": request.url.path}
            )
            raise unauthorized("Falta API key. Enviá el header X-API-Key.")

        # R: si hay API_KEYS_CONFIG, validamos key (const-time).
        validator = APIKeyValidator(keys_cfg) if keys_cfg else None
        if validator and not validator.validate_key(api_key):
            logger.warning(
                "Auth falló: API key inválida",
                extra={"key_hash": _hash_key(api_key), "path": request.url.path},
            )
            raise forbidden("API key inválida.")

        key_hash = _hash_key(api_key)
        request.state.api_key_hash = key_hash  # para dual_auth y/o logs.

        # R: Si no se requieren permisos específicos, solo autenticación.
        if not required:
            return None

        # 1) RBAC (roles/permisos).
        if rbac_cfg:
            allowed = any(
                rbac_cfg.check_permission(key_hash, perm) for perm in required
            )
            if not allowed:
                logger.warning(
                    "RBAC denegó",
                    extra={
                        "key_hash": key_hash[:8] + "...",
                        "permissions": [p.value for p in required],
                        "path": request.url.path,
                    },
                )
                raise forbidden(
                    "Permisos insuficientes. Requerido: "
                    + ", ".join(sorted(p.value for p in required))
                )
            return None

        # 2) Fallback por scopes (si no hay RBAC).
        if not validator:
            return None

        scopes = set(validator.get_scopes(api_key))
        if "*" in scopes:
            return None

        required_scopes = _required_scopes_for_permissions(required)
        if not required_scopes:
            raise forbidden("No hay mapeo de scopes para los permisos requeridos.")

        if not scopes.intersection(required_scopes):
            raise forbidden(
                "La API key no tiene el scope requerido: "
                + ", ".join(sorted(required_scopes))
            )

        return None

    # R: anotación útil para tests/introspección.
    dependency._required_permissions = tuple(p.value for p in required)
    return dependency


def require_permission(permission: Permission) -> Callable:
    """Atajo: requiere un permiso."""
    return require_permissions(permission)


def require_metrics_permission() -> Callable:
    """Auth opcional para /metrics según settings (metrics_require_auth)."""

    async def dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        from ..crosscutting.config import get_settings

        if not get_settings().metrics_require_auth:
            return None

        await require_permissions(Permission.ADMIN_METRICS)(request, api_key)
        return None

    return dependency


def require_role(role_name: str) -> Callable:
    """Dependency FastAPI: requiere un rol específico (solo si RBAC está habilitado)."""

    async def dependency(request: Request) -> None:
        rbac_cfg = get_rbac_config()
        if not rbac_cfg:
            return None

        key_hash = getattr(request.state, "api_key_hash", None)
        if not key_hash:
            raise forbidden("RBAC requiere request autenticado (API key).")

        user_role = rbac_cfg.get_role_for_key(key_hash)
        if not user_role:
            raise forbidden("No hay rol asignado a esta API key.")

        required_role = rbac_cfg.roles.get(role_name)
        if not required_role:
            logger.error("Rol requerido desconocido", extra={"role_name": role_name})
            raise forbidden("Configuración RBAC inválida.")

        # R: admin (* ) pasa siempre.
        if Permission.ALL in user_role.permissions:
            return None

        # Exacto o herencia
        if user_role.name == role_name:
            return None

        current = user_role
        while current.inherits_from:
            if current.inherits_from == role_name:
                return None
            current = rbac_cfg.roles.get(
                current.inherits_from
            )  # puede volverse None si config está mal
            if not current:
                break

        raise forbidden(f"Rol requerido: {role_name}. Tu rol: {user_role.name}")

    return dependency
