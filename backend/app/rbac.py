"""
Name: Role-Based Access Control (RBAC)

Responsibilities:
  - Define roles with hierarchical permissions
  - Map API keys to roles
  - Provide role-based authorization checks
  - Support custom resource-level permissions

Collaborators:
  - auth.py: API key validation
  - config.py: RBAC_CONFIG setting
  - routes.py: Depends(require_role) on endpoints

Constraints:
  - Roles are hierarchical (admin > user > readonly)
  - Resource permissions follow CRUD model
  - Configuration via environment variable (JSON)

Notes:
  - Complements API key scopes with fine-grained control
  - Wildcard (*) grants all permissions
  - Supports resource-level access (e.g., "documents:read")
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Callable, Optional, Set

from fastapi import HTTPException, Request

from .logger import logger


class Permission(Enum):
    """Available permissions in the system."""
    
    # Document operations
    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_DELETE = "documents:delete"
    
    # Query operations
    QUERY_SEARCH = "query:search"
    QUERY_ASK = "query:ask"
    QUERY_STREAM = "query:stream"
    
    # Admin operations
    ADMIN_METRICS = "admin:metrics"
    ADMIN_HEALTH = "admin:health"
    ADMIN_CONFIG = "admin:config"
    
    # Wildcard
    ALL = "*"


@dataclass
class Role:
    """Role definition with associated permissions."""
    
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    inherits_from: Optional[str] = None
    description: str = ""
    
    def has_permission(self, permission: Permission, roles_registry: dict) -> bool:
        """Check if role has permission (including inherited)."""
        # Wildcard grants all
        if Permission.ALL in self.permissions:
            return True
        
        # Direct permission
        if permission in self.permissions:
            return True
        
        # Check inherited role
        if self.inherits_from and self.inherits_from in roles_registry:
            parent_role = roles_registry[self.inherits_from]
            return parent_role.has_permission(permission, roles_registry)
        
        return False


# Default role definitions
DEFAULT_ROLES: dict[str, Role] = {
    "admin": Role(
        name="admin",
        permissions={Permission.ALL},
        description="Full system access",
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
        description="Standard user with read/write access",
    ),
    "readonly": Role(
        name="readonly",
        permissions={
            Permission.DOCUMENTS_READ,
            Permission.QUERY_SEARCH,
            Permission.QUERY_ASK,
        },
        description="Read-only access to documents and queries",
    ),
    "ingest-only": Role(
        name="ingest-only",
        permissions={
            Permission.DOCUMENTS_CREATE,
        },
        description="Can only ingest documents (for automation)",
    ),
}


@dataclass
class RBACConfig:
    """RBAC configuration with roles and key-role mappings."""
    
    roles: dict[str, Role]
    key_roles: dict[str, str]  # api_key_hash -> role_name
    
    def get_role_for_key(self, key_hash: str) -> Optional[Role]:
        """Get role assigned to an API key."""
        role_name = self.key_roles.get(key_hash)
        if role_name:
            return self.roles.get(role_name)
        return None
    
    def check_permission(self, key_hash: str, permission: Permission) -> bool:
        """Check if API key has a specific permission."""
        role = self.get_role_for_key(key_hash)
        if not role:
            return False
        return role.has_permission(permission, self.roles)


@lru_cache(maxsize=1)
def _parse_rbac_config() -> Optional[RBACConfig]:
    """
    Parse RBAC_CONFIG from environment.
    
    Format:
    {
        "roles": {
            "custom-role": {
                "permissions": ["documents:read", "query:search"],
                "inherits_from": "readonly"
            }
        },
        "key_roles": {
            "abc123...": "admin",
            "def456...": "user"
        }
    }
    """
    import os
    
    config_str = os.getenv("RBAC_CONFIG")
    if not config_str:
        return None
    
    try:
        data = json.loads(config_str)
        
        # Start with default roles
        roles = DEFAULT_ROLES.copy()
        
        # Add/override custom roles
        if "roles" in data:
            for role_name, role_data in data["roles"].items():
                permissions = {
                    Permission(p) for p in role_data.get("permissions", [])
                }
                roles[role_name] = Role(
                    name=role_name,
                    permissions=permissions,
                    inherits_from=role_data.get("inherits_from"),
                    description=role_data.get("description", ""),
                )
        
        # Parse key-role mappings
        key_roles = data.get("key_roles", {})
        
        return RBACConfig(roles=roles, key_roles=key_roles)
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Invalid RBAC_CONFIG: {e}")
        return None


def get_rbac_config() -> Optional[RBACConfig]:
    """Get RBAC configuration (cached)."""
    return _parse_rbac_config()


def clear_rbac_cache() -> None:
    """Clear RBAC config cache (for testing)."""
    _parse_rbac_config.cache_clear()


def is_rbac_enabled() -> bool:
    """Check if RBAC is configured."""
    return get_rbac_config() is not None


def require_permission(permission: Permission) -> Callable:
    """
    FastAPI dependency that requires a specific permission.
    
    Usage:
        @router.post("/ingest/text")
        def ingest(
            req: Request,
            _: None = Depends(require_permission(Permission.DOCUMENTS_CREATE))
        ):
            ...
    
    Raises:
        HTTPException 403: Insufficient permissions
    
    Note: Falls back to scope-based auth if RBAC is not configured.
    """
    
    async def dependency(request: Request) -> None:
        rbac_config = get_rbac_config()
        
        # If RBAC not configured, fall back to scope-based auth
        if not rbac_config:
            return None
        
        # Get API key hash from request state (set by auth.py)
        key_hash = getattr(request.state, "api_key_hash", None)
        
        if not key_hash:
            # No API key provided - check if auth is required
            from .auth import is_auth_enabled
            if is_auth_enabled():
                raise HTTPException(
                    status_code=403,
                    detail="RBAC requires authenticated request",
                )
            return None
        
        # Check permission
        if not rbac_config.check_permission(key_hash, permission):
            logger.warning(
                "RBAC denied",
                extra={
                    "key_hash": key_hash[:8] + "...",
                    "permission": permission.value,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {permission.value}",
            )
        
        return None
    
    return dependency


def require_role(role_name: str) -> Callable:
    """
    FastAPI dependency that requires a specific role.
    
    Usage:
        @router.delete("/admin/cache")
        def clear_cache(_: None = Depends(require_role("admin"))):
            ...
    """
    
    async def dependency(request: Request) -> None:
        rbac_config = get_rbac_config()
        
        if not rbac_config:
            return None
        
        key_hash = getattr(request.state, "api_key_hash", None)
        
        if not key_hash:
            from .auth import is_auth_enabled
            if is_auth_enabled():
                raise HTTPException(
                    status_code=403,
                    detail="RBAC requires authenticated request",
                )
            return None
        
        # Get user's role
        user_role = rbac_config.get_role_for_key(key_hash)
        
        if not user_role:
            raise HTTPException(
                status_code=403,
                detail="No role assigned to this API key",
            )
        
        # Check if user has required role (or inherits from it)
        required_role = rbac_config.roles.get(role_name)
        if not required_role:
            logger.warning(f"Unknown role requested: {role_name}")
            raise HTTPException(
                status_code=500,
                detail="Invalid role configuration",
            )
        
        # Admin role has access to everything
        if Permission.ALL in user_role.permissions:
            return None
        
        # Check exact role match
        if user_role.name == role_name:
            return None
        
        # Check inheritance chain
        current = user_role
        while current.inherits_from:
            if current.inherits_from == role_name:
                return None
            current = rbac_config.roles.get(current.inherits_from)
            if not current:
                break
        
        raise HTTPException(
            status_code=403,
            detail=f"Required role: {role_name}. Your role: {user_role.name}",
        )
    
    return dependency
