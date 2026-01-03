"""
Name: Security Hardening Tests

Responsibilities:
  - Test body size limit middleware
  - Test secret redaction in logs
  - Test CORS configuration

Notes:
  - Unit tests (no external dependencies)
  - Uses mocking for config and requests
"""

import pytest
import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
class TestBodyLimitMiddleware:
    """Test BodyLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_small_body(self):
        """Bodies under limit should pass."""
        from app.middleware import BodyLimitMiddleware
        
        # R: Mock the call_next to return a response
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)
        
        # R: Mock request with small body
        mock_request = MagicMock()
        mock_request.headers = {"content-length": "1000"}
        mock_request.url.path = "/v1/ingest/text"
        
        middleware = BodyLimitMiddleware(app=MagicMock())
        
        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.max_body_bytes = 10_000_000  # 10MB
            
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # R: Should call next middleware
        mock_call_next.assert_called_once()
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_rejects_large_body(self):
        """Bodies over limit should return 413."""
        from app.middleware import BodyLimitMiddleware
        
        mock_call_next = AsyncMock()
        
        # R: Mock request with large body
        mock_request = MagicMock()
        mock_request.headers = {"content-length": "20000000"}  # 20MB
        mock_request.url.path = "/v1/ingest/text"
        
        middleware = BodyLimitMiddleware(app=MagicMock())
        
        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.max_body_bytes = 10_000_000  # 10MB limit
            
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # R: Should NOT call next middleware
        mock_call_next.assert_not_called()
        
        # R: Should return 413
        assert response.status_code == 413
        body = json.loads(response.body)
        assert "too large" in body["detail"].lower()

    @pytest.mark.asyncio
    async def test_allows_request_without_content_length(self):
        """Requests without Content-Length should pass."""
        from app.middleware import BodyLimitMiddleware
        
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)
        
        # R: Mock request without content-length
        mock_request = MagicMock()
        mock_request.headers = {}  # No content-length
        
        middleware = BodyLimitMiddleware(app=MagicMock())
        
        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.max_body_bytes = 10_000_000
            
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # R: Should pass through
        mock_call_next.assert_called_once()


@pytest.mark.unit
class TestSecretRedaction:
    """Test that secrets are never logged."""

    def test_api_key_not_in_json_log(self):
        """API key field should be filtered from logs."""
        from app.logger import JSONFormatter
        
        formatter = JSONFormatter()
        
        # R: Create log record with api_key in extra
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.api_key = "super-secret-key"
        
        output = formatter.format(record)
        log_dict = json.loads(output)
        
        # R: api_key should NOT be in output
        assert "api_key" not in log_dict
        assert "super-secret-key" not in output

    def test_google_api_key_not_in_log(self):
        """Google API key should be filtered from logs."""
        from app.logger import JSONFormatter
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.google_api_key = "AIza-super-secret"
        
        output = formatter.format(record)
        
        assert "google_api_key" not in output
        assert "AIza-super-secret" not in output

    def test_authorization_header_not_in_log(self):
        """Authorization header should be filtered from logs."""
        from app.logger import JSONFormatter
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.authorization = "Bearer secret-token"
        
        output = formatter.format(record)
        
        assert "authorization" not in output
        assert "secret-token" not in output

    def test_non_sensitive_fields_are_logged(self):
        """Non-sensitive extra fields should be logged."""
        from app.logger import JSONFormatter
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc-123"
        record.user_id = "user-456"
        
        output = formatter.format(record)
        log_dict = json.loads(output)
        
        # R: Non-sensitive fields should be present
        assert log_dict.get("request_id") == "abc-123"
        assert log_dict.get("user_id") == "user-456"

    def test_all_sensitive_keys_are_filtered(self):
        """All keys in SENSITIVE_KEYS should be filtered."""
        from app.logger import JSONFormatter
        
        sensitive_keys = [
            "password", "api_key", "secret", "token", "authorization",
            "google_api_key", "x-api-key", "apikey", "api_keys_config",
            "credential", "private_key", "access_token", "refresh_token",
        ]
        
        formatter = JSONFormatter()
        
        for key in sensitive_keys:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            setattr(record, key, f"secret-value-{key}")
            
            output = formatter.format(record)
            
            assert key not in output.lower(), f"Sensitive key '{key}' was logged"
            assert f"secret-value-{key}" not in output, f"Value for '{key}' was logged"


@pytest.mark.unit
class TestCORSConfiguration:
    """Test CORS security settings."""

    def test_cors_allow_credentials_default_is_false(self):
        """Default for cors_allow_credentials should be False."""
        from app.config import Settings
        
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "GOOGLE_API_KEY": "test-key",
        }):
            settings = Settings()
            assert settings.cors_allow_credentials is False

    def test_cors_allow_credentials_can_be_enabled(self):
        """cors_allow_credentials can be set to True."""
        from app.config import Settings
        
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "GOOGLE_API_KEY": "test-key",
            "CORS_ALLOW_CREDENTIALS": "true",
        }):
            settings = Settings()
            assert settings.cors_allow_credentials is True


@pytest.mark.unit
class TestMaxBodyBytesConfig:
    """Test max body bytes configuration."""

    def test_default_max_body_bytes(self):
        """Default max_body_bytes should be 10MB."""
        from app.config import Settings
        
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "GOOGLE_API_KEY": "test-key",
        }):
            settings = Settings()
            assert settings.max_body_bytes == 10 * 1024 * 1024  # 10MB

    def test_custom_max_body_bytes(self):
        """max_body_bytes can be customized."""
        from app.config import Settings
        
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "GOOGLE_API_KEY": "test-key",
            "MAX_BODY_BYTES": "5242880",  # 5MB
        }):
            settings = Settings()
            assert settings.max_body_bytes == 5242880
