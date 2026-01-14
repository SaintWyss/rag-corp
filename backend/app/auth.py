"""
Name: API Key Authentication

Responsibilities:
  - Validate API keys from X-API-Key header
  - Check scopes (ingest, ask, metrics)
  - Constant-time comparison to prevent timing attacks
  - Return 401 for missing key, 403 for invalid/insufficient scope

Collaborators:
  - config.py: API_KEYS_CONFIG setting
  - routes.py: Depends(require_scope) on endpoints
  - logger.py: Log auth failures (with key hash, not raw key)

Constraints:
  - No business logic - pure authentication/authorization
  - Keys stored in env var, not database (stateless)
  - Never log raw API keys

Notes:
  - Scopes: "ingest" (POST /v1/ingest/*), "ask" (POST /v1/query, /v1/ask)
  - Special scope "metrics" for /metrics endpoint (optional)
  - Keys config format: {"key1": ["scope1", "scope2"], ...}
"""

import hashlib
import hmac
import json
from typing import Callable
from functools import lru_cache

from fastapi import Header, Request
from fastapi.security import APIKeyHeader

from .error_responses import forbidden, unauthorized
from .logger import logger


def _hash_key(key: str) -> str:
    """R: Hash API key for safe logging (never log raw keys)."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _constant_time_compare(a: str, b: str) -> bool:
    """R: Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


@lru_cache(maxsize=1)
def _parse_keys_config() -> dict[str, list[str]]:
    """
    R: Parse API_KEYS_CONFIG from environment.

    Format: JSON object {"key": ["scope1", "scope2"], ...}
    Example: {"secret-key-1": ["ingest", "ask"], "read-only": ["ask"]}

    Returns empty dict if not configured (auth disabled).
    """
    from .config import get_settings

    config_str = get_settings().api_keys_config
    if not config_str:
        return {}

    try:
        config = json.loads(config_str)
        if not isinstance(config, dict):
            logger.warning("API_KEYS_CONFIG must be a JSON object, auth disabled")
            return {}
        return config
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid API_KEYS_CONFIG JSON: {e}, auth disabled")
        return {}


def get_keys_config() -> dict[str, list[str]]:
    """R: Get parsed keys config (allows cache clearing in tests)."""
    return _parse_keys_config()


def clear_keys_cache() -> None:
    """R: Clear keys config cache (for testing)."""
    _parse_keys_config.cache_clear()


def is_auth_enabled() -> bool:
    """R: Check if authentication is configured."""
    return bool(get_keys_config())


class APIKeyValidator:
    """
    R: Validates API keys and scopes.

    Methods:
        validate_key: Check if key exists (constant-time)
        validate_scope: Check if key has required scope
        get_scopes: Get scopes for a valid key
    """

    def __init__(self, keys_config: dict[str, list[str]]):
        self._keys = keys_config

    def validate_key(self, key: str) -> bool:
        """R: Check if key is valid using constant-time comparison."""
        if not key:
            return False

        # R: Compare against all keys to maintain constant time
        found = False
        for valid_key in self._keys.keys():
            if _constant_time_compare(key, valid_key):
                found = True
        return found

    def get_scopes(self, key: str) -> list[str]:
        """R: Get scopes for a key (empty if invalid)."""
        for valid_key, scopes in self._keys.items():
            if _constant_time_compare(key, valid_key):
                return scopes
        return []

    def validate_scope(self, key: str, required_scope: str) -> bool:
        """R: Check if key has required scope."""
        scopes = self.get_scopes(key)
        return required_scope in scopes or "*" in scopes


# R: FastAPI security scheme for OpenAPI docs
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_scope(scope: str) -> Callable:
    """
    R: FastAPI dependency that requires a valid API key with scope.

    Usage:
        @router.post("/ingest/text")
        def ingest(req: Request, _: None = Depends(require_scope("ingest"))):
            ...

    Raises:
        HTTPException 401: Missing API key
        HTTPException 403: Invalid key or insufficient scope

    Returns None if auth is disabled (no keys configured).
    """

    async def dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        keys_config = get_keys_config()

        # R: If no keys configured, auth is disabled
        if not keys_config:
            return None

        # R: Missing key -> 401 Unauthorized
        if not api_key:
            logger.warning(
                "Auth failed: missing API key",
                extra={"path": request.url.path, "scope": scope},
            )
            raise unauthorized("Missing API key. Provide X-API-Key header.")

        validator = APIKeyValidator(keys_config)

        # R: Invalid key -> 403 Forbidden
        if not validator.validate_key(api_key):
            logger.warning(
                "Auth failed: invalid API key",
                extra={
                    "key_hash": _hash_key(api_key),
                    "path": request.url.path,
                    "scope": scope,
                },
            )
            raise forbidden("Invalid API key.")

        # R: Key without required scope -> 403 Forbidden
        if not validator.validate_scope(api_key, scope):
            logger.warning(
                "Auth failed: insufficient scope",
                extra={
                    "key_hash": _hash_key(api_key),
                    "path": request.url.path,
                    "required_scope": scope,
                    "available_scopes": validator.get_scopes(api_key),
                },
            )
            raise forbidden(f"API key does not have required scope: {scope}")

        # R: Store key hash in request state for rate limiting
        request.state.api_key_hash = _hash_key(api_key)
        return None

    return dependency


def require_metrics_auth() -> Callable:
    """
    R: Optional auth for /metrics endpoint.

    Only enforced if METRICS_REQUIRE_AUTH=true.
    """

    async def dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        from .config import get_settings

        if not get_settings().metrics_require_auth:
            return None

        # R: Reuse require_scope logic
        await require_scope("metrics")(request, api_key)
        return None

    return dependency
