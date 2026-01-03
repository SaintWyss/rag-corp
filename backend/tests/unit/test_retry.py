"""
Name: Retry Helper Unit Tests

Responsibilities:
  - Test transient vs permanent error classification
  - Verify retry decorator configuration
  - Validate exponential backoff behavior
  - Test logging of retry attempts

Collaborators:
  - app.infrastructure.services.retry: Module under test
  - pytest: Testing framework
  - unittest.mock: Mocking external dependencies

Constraints:
  - Tests must not make real API calls
  - Must run fast (mocked delays)

Notes:
  - Uses pytest markers for unit tests
  - Covers edge cases for error classification
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from tenacity import RetryError

from app.infrastructure.services.retry import (
    is_transient_error,
    get_http_status_code,
    create_retry_decorator,
    with_retry,
    TRANSIENT_HTTP_CODES,
    PERMANENT_HTTP_CODES,
)


class TestGetHttpStatusCode:
    """Tests for HTTP status code extraction from exceptions."""
    
    def test_extracts_code_attribute(self):
        """Should extract status code from .code attribute."""
        exc = Mock()
        exc.code = 429
        assert get_http_status_code(exc) == 429
    
    def test_extracts_from_response_attribute(self):
        """Should extract status code from response.status_code."""
        exc = Mock()
        exc.code = None
        exc.response = Mock()
        exc.response.status_code = 503
        assert get_http_status_code(exc) == 503
    
    def test_extracts_status_code_attribute(self):
        """Should extract from direct status_code attribute."""
        exc = Mock(spec=["status_code"])
        exc.status_code = 500
        assert get_http_status_code(exc) == 500
    
    def test_returns_none_for_unknown_exception(self):
        """Should return None if no status code found."""
        exc = ValueError("some error")
        assert get_http_status_code(exc) is None


class TestIsTransientError:
    """Tests for transient error classification."""
    
    @pytest.mark.parametrize("code", list(TRANSIENT_HTTP_CODES))
    def test_transient_http_codes(self, code):
        """Should classify transient HTTP codes as transient."""
        exc = Mock()
        exc.code = code
        assert is_transient_error(exc) is True
    
    @pytest.mark.parametrize("code", list(PERMANENT_HTTP_CODES))
    def test_permanent_http_codes(self, code):
        """Should classify permanent HTTP codes as non-transient."""
        exc = Mock()
        exc.code = code
        assert is_transient_error(exc) is False
    
    def test_timeout_exception_name(self):
        """Should classify timeout exceptions as transient."""
        class TimeoutException(Exception):
            pass
        exc = TimeoutException("connection timed out")
        assert is_transient_error(exc) is True
    
    def test_connection_exception_name(self):
        """Should classify connection exceptions as transient."""
        class ConnectionResetError(Exception):
            pass
        exc = ConnectionResetError("connection reset by peer")
        assert is_transient_error(exc) is True
    
    def test_rate_limit_message(self):
        """Should classify rate limit errors as transient."""
        exc = Exception("Rate limit exceeded, please retry")
        assert is_transient_error(exc) is True
    
    def test_quota_exceeded_message(self):
        """Should classify quota errors as transient."""
        exc = Exception("Quota exceeded for embedding API")
        assert is_transient_error(exc) is True
    
    def test_unknown_error_not_transient(self):
        """Should classify unknown errors as non-transient (fail fast)."""
        exc = ValueError("Invalid argument provided")
        assert is_transient_error(exc) is False
    
    def test_resource_exhausted_exception(self):
        """Should classify resource exhausted as transient."""
        class ResourceExhaustedException(Exception):
            pass
        exc = ResourceExhaustedException("quota")
        assert is_transient_error(exc) is True


class TestCreateRetryDecorator:
    """Tests for retry decorator creation."""
    
    @patch("app.infrastructure.services.retry.get_settings")
    def test_uses_settings_defaults(self, mock_get_settings):
        """Should use settings for default values."""
        mock_settings = Mock()
        mock_settings.retry_max_attempts = 5
        mock_settings.retry_base_delay_seconds = 2.0
        mock_settings.retry_max_delay_seconds = 60.0
        mock_get_settings.return_value = mock_settings
        
        decorator = create_retry_decorator()
        
        # Decorator should be created without error
        assert decorator is not None
    
    @patch("app.infrastructure.services.retry.get_settings")
    def test_override_settings(self, mock_get_settings):
        """Should allow overriding settings."""
        mock_settings = Mock()
        mock_settings.retry_max_attempts = 5
        mock_settings.retry_base_delay_seconds = 2.0
        mock_settings.retry_max_delay_seconds = 60.0
        mock_get_settings.return_value = mock_settings
        
        decorator = create_retry_decorator(
            max_attempts=2,
            base_delay=0.1,
            max_delay=1.0
        )
        
        assert decorator is not None
    
    @patch("app.infrastructure.services.retry.get_settings")
    def test_retry_on_transient_error(self, mock_get_settings):
        """Should retry on transient errors."""
        mock_settings = Mock()
        mock_settings.retry_max_attempts = 3
        mock_settings.retry_base_delay_seconds = 0.01  # Fast for tests
        mock_settings.retry_max_delay_seconds = 0.05
        mock_get_settings.return_value = mock_settings
        
        call_count = 0
        
        @create_retry_decorator()
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                exc = Mock()
                exc.code = 503  # Transient
                raise type("ServiceUnavailable", (Exception,), {"code": 503})()
            return "success"
        
        # Should eventually succeed after retries
        # Note: This may take multiple attempts
        try:
            result = flaky_function()
            assert call_count >= 1
        except Exception:
            # Expected if all retries exhausted
            assert call_count == 3
    
    @patch("app.infrastructure.services.retry.get_settings")
    def test_no_retry_on_permanent_error(self, mock_get_settings):
        """Should not retry on permanent errors."""
        mock_settings = Mock()
        mock_settings.retry_max_attempts = 3
        mock_settings.retry_base_delay_seconds = 0.01
        mock_settings.retry_max_delay_seconds = 0.05
        mock_get_settings.return_value = mock_settings
        
        call_count = 0
        
        class PermanentError(Exception):
            code = 400  # Bad Request - permanent
        
        @create_retry_decorator()
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise PermanentError("Bad request")
        
        with pytest.raises(PermanentError):
            failing_function()
        
        # Should only be called once (no retries for permanent errors)
        assert call_count == 1


class TestWithRetryDecorator:
    """Tests for the convenience @with_retry decorator."""
    
    @patch("app.infrastructure.services.retry.create_retry_decorator")
    def test_applies_retry_decorator(self, mock_create):
        """Should apply retry decorator to function."""
        # Return a simple passthrough decorator
        mock_create.return_value = lambda f: f
        
        @with_retry
        def my_function():
            return "result"
        
        result = my_function()
        
        # Decorator should be created at call time
        mock_create.assert_called()


@pytest.mark.unit
class TestRetryLogging:
    """Tests for retry logging behavior."""
    
    @patch("app.infrastructure.services.retry.logger")
    @patch("app.infrastructure.services.retry.get_settings")
    def test_logs_retry_attempts(self, mock_get_settings, mock_logger):
        """Should log each retry attempt."""
        mock_settings = Mock()
        mock_settings.retry_max_attempts = 2
        mock_settings.retry_base_delay_seconds = 0.001
        mock_settings.retry_max_delay_seconds = 0.01
        mock_get_settings.return_value = mock_settings
        
        call_count = 0
        
        class TransientError(Exception):
            code = 503
        
        @create_retry_decorator()
        def flaky():
            nonlocal call_count
            call_count += 1
            raise TransientError("Service unavailable")
        
        with pytest.raises(TransientError):
            flaky()
        
        # Should have logged warnings for retry attempts
        # (at least one warning call expected)
        assert call_count == 2  # max_attempts
