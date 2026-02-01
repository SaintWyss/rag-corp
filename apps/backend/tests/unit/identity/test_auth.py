"""
Name: API Key Authentication Tests

Responsibilities:
  - Test API key validation
  - Test scope authorization
  - Test constant-time comparison
  - Test error responses (401, 403)

Notes:
  - Unit tests (no external dependencies)
  - Uses mocking for config
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestAPIKeyValidator:
    """Test APIKeyValidator class."""

    def test_validate_key_returns_true_for_valid_key(self):
        """Valid key should be accepted."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ask"]})
        assert validator.validate_key("test-key") is True

    def test_validate_key_returns_false_for_invalid_key(self):
        """Invalid key should be rejected."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ask"]})
        assert validator.validate_key("wrong-key") is False

    def test_validate_key_returns_false_for_empty_key(self):
        """Empty key should be rejected."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ask"]})
        assert validator.validate_key("") is False

    def test_validate_scope_returns_true_when_has_scope(self):
        """Key with required scope should pass."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ingest", "ask"]})
        assert validator.validate_scope("test-key", "ingest") is True
        assert validator.validate_scope("test-key", "ask") is True

    def test_validate_scope_returns_false_when_missing_scope(self):
        """Key without required scope should fail."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ask"]})
        assert validator.validate_scope("test-key", "ingest") is False

    def test_wildcard_scope_grants_all_access(self):
        """Wildcard scope '*' should grant all access."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"admin-key": ["*"]})
        assert validator.validate_scope("admin-key", "ingest") is True
        assert validator.validate_scope("admin-key", "ask") is True
        assert validator.validate_scope("admin-key", "anything") is True

    def test_get_scopes_returns_scopes_for_valid_key(self):
        """Get scopes should return list for valid key."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ingest", "ask"]})
        scopes = validator.get_scopes("test-key")
        assert scopes == ["ingest", "ask"]

    def test_get_scopes_returns_empty_for_invalid_key(self):
        """Get scopes should return empty list for invalid key."""
        from app.identity.auth import APIKeyValidator

        validator = APIKeyValidator({"test-key": ["ask"]})
        assert validator.get_scopes("wrong-key") == []


@pytest.mark.unit
class TestConstantTimeCompare:
    """Test constant-time comparison function."""

    def test_constant_time_compare_equal_strings(self):
        """Equal strings should return True."""
        from app.identity.auth import _constant_time_compare

        assert _constant_time_compare("abc", "abc") is True

    def test_constant_time_compare_different_strings(self):
        """Different strings should return False."""
        from app.identity.auth import _constant_time_compare

        assert _constant_time_compare("abc", "xyz") is False

    def test_constant_time_compare_different_lengths(self):
        """Strings of different length should return False."""
        from app.identity.auth import _constant_time_compare

        assert _constant_time_compare("abc", "abcd") is False

    def test_constant_time_compare_uses_hmac(self):
        """
        Verify we use hmac.compare_digest for constant-time comparison.

        Note: Actual timing tests are unreliable in unit tests.
        We verify the implementation uses the correct algorithm.
        """
        import hmac

        from app.identity.auth import _constant_time_compare

        # R: Verify our function behaves like hmac.compare_digest
        test_cases = [
            ("abc", "abc", True),
            ("abc", "xyz", False),
            ("", "", True),
            ("a", "b", False),
        ]

        for a, b, expected in test_cases:
            assert _constant_time_compare(a, b) == expected
            assert _constant_time_compare(a, b) == hmac.compare_digest(
                a.encode(), b.encode()
            )


@pytest.mark.unit
class TestHashKey:
    """Test key hashing for safe logging."""

    def test_hash_key_returns_12_char_string(self):
        """Hash should be truncated to 12 characters."""
        from app.identity.auth import _hash_key

        result = _hash_key("test-key")
        assert len(result) == 12

    def test_hash_key_is_deterministic(self):
        """Same input should produce same hash."""
        from app.identity.auth import _hash_key

        hash1 = _hash_key("test-key")
        hash2 = _hash_key("test-key")
        assert hash1 == hash2

    def test_hash_key_different_for_different_keys(self):
        """Different keys should produce different hashes."""
        from app.identity.auth import _hash_key

        hash1 = _hash_key("key-1")
        hash2 = _hash_key("key-2")
        assert hash1 != hash2


@pytest.mark.unit
class TestParseKeysConfig:
    """Test keys config parsing."""

    def test_parse_valid_json_config(self):
        """Valid JSON should be parsed correctly."""
        from app.identity.auth import _parse_keys_config, clear_keys_cache

        clear_keys_cache()

        with patch("app.crosscutting.config.get_settings") as mock_settings:
            mock_settings.return_value.api_keys_config = (
                '{"key1": ["ask"], "key2": ["ingest"]}'
            )
            result = _parse_keys_config()

        clear_keys_cache()

        assert result == {"key1": ["ask"], "key2": ["ingest"]}

    def test_parse_empty_config_returns_empty_dict(self):
        """Empty config should return empty dict (auth disabled)."""
        from app.identity.auth import _parse_keys_config, clear_keys_cache

        clear_keys_cache()

        with patch("app.crosscutting.config.get_settings") as mock_settings:
            mock_settings.return_value.api_keys_config = ""
            result = _parse_keys_config()

        clear_keys_cache()

        assert result == {}

    def test_parse_invalid_json_returns_empty_dict(self):
        """Invalid JSON should return empty dict with warning."""
        from app.identity.auth import _parse_keys_config, clear_keys_cache

        clear_keys_cache()

        with patch("app.crosscutting.config.get_settings") as mock_settings:
            mock_settings.return_value.api_keys_config = "not-valid-json"
            result = _parse_keys_config()

        clear_keys_cache()

        assert result == {}


@pytest.mark.unit
class TestRequireScopeErrors:
    """Test require_scope error conditions."""

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self):
        """Missing API key should raise 401."""
        from app.identity.auth import clear_keys_cache, require_scope
        from fastapi import HTTPException

        clear_keys_cache()

        with patch("app.identity.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ask"]}

            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"

            dependency = require_scope("ask")

            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, None)  # No API key

            assert exc_info.value.status_code == 401
            assert (
                "API key" in exc_info.value.detail or "Falta" in exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_invalid_key_raises_403(self):
        """Invalid API key should raise 403."""
        from app.identity.auth import clear_keys_cache, require_scope
        from fastapi import HTTPException

        clear_keys_cache()

        with patch("app.identity.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ask"]}

            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"

            dependency = require_scope("ask")

            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, "wrong-key")

            assert exc_info.value.status_code == 403
            assert (
                "API key" in exc_info.value.detail
                or "inv\xe1lida" in exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_key_without_scope_raises_403(self):
        """Key without required scope should raise 403."""
        from app.identity.auth import clear_keys_cache, require_scope
        from fastapi import HTTPException

        clear_keys_cache()

        with patch("app.identity.auth.get_keys_config") as mock_config:
            mock_config.return_value = {
                "read-only-key": ["ask"]
            }  # Only has "ask" scope

            mock_request = MagicMock()
            mock_request.url.path = "/v1/ingest/text"
            mock_request.state = MagicMock()

            dependency = require_scope("ingest")  # Requires "ingest" scope

            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_request, "read-only-key")

            assert exc_info.value.status_code == 403
            assert (
                "scope" in exc_info.value.detail
                or "inv\xe1lida" in exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_valid_key_with_scope_passes(self):
        """Valid key with required scope should pass."""
        from app.identity.auth import clear_keys_cache, require_scope

        clear_keys_cache()

        with patch("app.identity.auth.get_keys_config") as mock_config:
            mock_config.return_value = {"valid-key": ["ask", "ingest"]}

            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"
            mock_request.state = MagicMock()

            dependency = require_scope("ask")

            # R: Should not raise
            result = await dependency(mock_request, "valid-key")
            assert result is None

    @pytest.mark.asyncio
    async def test_auth_disabled_when_no_keys_configured(self):
        """When no keys configured, auth should be disabled."""
        from app.identity.auth import clear_keys_cache, require_scope

        clear_keys_cache()

        with patch("app.identity.auth.get_keys_config") as mock_config:
            mock_config.return_value = {}  # No keys = auth disabled

            mock_request = MagicMock()
            mock_request.url.path = "/v1/ask"

            dependency = require_scope("ask")

            # R: Should pass without key when auth disabled
            result = await dependency(mock_request, None)
            assert result is None
