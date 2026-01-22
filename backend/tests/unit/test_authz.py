"""
Tests for authorization (RBAC + scope fallback).
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.auth import _hash_key, clear_keys_cache
from app.rbac import (
    DEFAULT_ROLES,
    Permission,
    RBACConfig,
    clear_rbac_cache,
    require_permissions,
)


@pytest.mark.unit
class TestRequirePermissions:
    """Tests for require_permissions dependency."""

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self):
        clear_keys_cache()
        clear_rbac_cache()

        with patch("app.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ask"]}
            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"

            dependency = require_permissions(Permission.QUERY_ASK)
            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, None)

            assert exc_info.value.status_code == 401
            assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_key_raises_403(self):
        clear_keys_cache()
        clear_rbac_cache()

        with patch("app.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ask"]}
            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"

            dependency = require_permissions(Permission.QUERY_ASK)
            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, "wrong-key")

            assert exc_info.value.status_code == 403
            assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_scope_missing_permission_raises_403(self):
        clear_keys_cache()
        clear_rbac_cache()

        with patch("app.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ingest"]}
            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"

            dependency = require_permissions(Permission.QUERY_ASK)
            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, "valid-key")

            assert exc_info.value.status_code == 403
            assert "required scope" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_scope_allows_and_sets_key_hash(self):
        clear_keys_cache()
        clear_rbac_cache()

        with patch("app.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ask"]}
            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"
            mock_request.state = MagicMock()

            dependency = require_permissions(Permission.QUERY_ASK)
            await dependency(mock_request, "valid-key")

            assert mock_request.state.api_key_hash == _hash_key("valid-key")

    @pytest.mark.asyncio
    async def test_rbac_enforced_when_configured(self):
        clear_keys_cache()
        clear_rbac_cache()

        key = "rbac-key"
        key_hash = _hash_key(key)
        rbac_config = RBACConfig(
            roles=DEFAULT_ROLES,
            key_roles={key_hash: "readonly"},
        )

        with (
            patch("app.auth.get_keys_config") as mock_config,
            patch("app.rbac.get_rbac_config") as mock_rbac,
        ):
            mock_config.return_value = {key: ["ask"]}
            mock_rbac.return_value = rbac_config

            mock_request = MagicMock()
            mock_request.url.path = "/v1/ingest/text"
            mock_request.state = MagicMock()

            dependency = require_permissions(Permission.DOCUMENTS_CREATE)
            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, key)

            assert exc_info.value.status_code == 403
            assert "Insufficient permissions" in exc_info.value.detail


@pytest.mark.unit
class TestRoutePermissions:
    """Ensure routes use RBAC permissions."""

    def test_routes_include_expected_permissions(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        import app.routes as routes

        importlib.reload(routes)

        expected = {
            "/ingest/text": Permission.DOCUMENTS_CREATE.value,
            "/ingest/batch": Permission.DOCUMENTS_CREATE.value,
            "/query": Permission.QUERY_SEARCH.value,
            "/ask": Permission.QUERY_ASK.value,
            "/ask/stream": Permission.QUERY_STREAM.value,
        }

        for route in routes.router.routes:
            if not isinstance(route, APIRoute):
                continue
            if route.path not in expected:
                continue
            required = set()
            for dep in route.dependant.dependencies:
                required.update(getattr(dep.call, "_required_permissions", ()))
            assert expected[route.path] in required
