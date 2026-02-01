"""
Name: Rate Limiter Tests

Responsibilities:
  - Test token bucket algorithm
  - Test burst behavior
  - Test refill over time
  - Test retry-after calculation

Notes:
  - Unit tests (no external dependencies)
  - Uses mocking for time
"""

import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestTokenBucket:
    """Test TokenBucket class."""

    def test_initial_bucket_is_full(self):
        """New bucket should have full tokens."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=10, burst=20)
        remaining = bucket.get_remaining("test-key")
        assert remaining == 20

    def test_consume_returns_true_when_tokens_available(self):
        """Consume should succeed when tokens available."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=10, burst=20)
        allowed, retry_after = bucket.consume("test-key")

        assert allowed is True
        assert retry_after == 0.0

    def test_consume_decrements_tokens(self):
        """Each consume should decrement tokens by 1."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=10, burst=5)

        bucket.consume("test-key")
        assert bucket.get_remaining("test-key") == 4

        bucket.consume("test-key")
        assert bucket.get_remaining("test-key") == 3

    def test_consume_blocks_after_burst_exhausted(self):
        """Consume should fail when burst is exhausted."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=10, burst=3)

        # R: Exhaust burst
        bucket.consume("test-key")
        bucket.consume("test-key")
        bucket.consume("test-key")

        # R: Next should be blocked
        allowed, retry_after = bucket.consume("test-key")

        assert allowed is False
        assert retry_after > 0

    def test_retry_after_is_positive_when_limited(self):
        """Retry-after should be positive when rate limited."""
        from app.crosscutting.rate_limit import TokenBucket

        # R: Create bucket with very slow refill
        bucket = TokenBucket(rps=0.001, burst=2)  # 0.001 token/sec

        # R: Exhaust both tokens immediately
        bucket.consume("test-key")
        bucket.consume("test-key")

        # R: Third request should be blocked
        allowed, retry_after = bucket.consume("test-key")

        assert allowed is False
        assert retry_after > 0

    def test_tokens_refill_over_time(self):
        """Tokens should refill at rps rate."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=100, burst=10)  # Fast refill for testing

        # R: Consume all tokens
        for _ in range(10):
            bucket.consume("test-key")

        assert bucket.get_remaining("test-key") == 0

        # R: Wait a bit for refill
        time.sleep(0.05)  # 50ms = 5 tokens at 100 rps

        remaining = bucket.get_remaining("test-key")
        assert 3 <= remaining <= 7  # Allow some timing variance

    def test_tokens_do_not_exceed_burst(self):
        """Refill should not exceed burst limit."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=1000, burst=5)

        # R: Consume one token
        bucket.consume("test-key")

        # R: Wait for potential overfill
        time.sleep(0.1)

        remaining = bucket.get_remaining("test-key")
        assert remaining == 5  # Should be capped at burst

    def test_separate_buckets_per_key(self):
        """Each key should have its own bucket."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=10, burst=3)

        # R: Exhaust key1
        bucket.consume("key1")
        bucket.consume("key1")
        bucket.consume("key1")

        # R: key2 should still have full bucket
        remaining = bucket.get_remaining("key2")
        assert remaining == 3

    def test_clear_resets_all_buckets(self):
        """Clear should reset all buckets."""
        from app.crosscutting.rate_limit import TokenBucket

        bucket = TokenBucket(rps=10, burst=5)

        # R: Consume some tokens
        bucket.consume("key1")
        bucket.consume("key2")

        # R: Clear all
        bucket.clear()

        # R: Both should be full again
        assert bucket.get_remaining("key1") == 5
        assert bucket.get_remaining("key2") == 5

    def test_invalid_rps_raises_error(self):
        """RPS must be positive."""
        from app.crosscutting.rate_limit import TokenBucket

        with pytest.raises(ValueError, match="rps debe ser > 0"):
            TokenBucket(rps=0, burst=10)

        with pytest.raises(ValueError, match="rps debe ser > 0"):
            TokenBucket(rps=-1, burst=10)

    def test_invalid_burst_raises_error(self):
        """Burst must be positive."""
        from app.crosscutting.rate_limit import TokenBucket

        with pytest.raises(ValueError, match="burst debe ser > 0"):
            TokenBucket(rps=10, burst=0)


@pytest.mark.unit
class TestGetClientIdentifier:
    """Test client identifier extraction."""

    def test_prefers_api_key_hash(self):
        """Should prefer API key hash if available."""
        from app.crosscutting.rate_limit import get_client_identifier

        mock_request = MagicMock()
        mock_request.state.api_key_hash = "abc123"
        mock_request.headers = {}
        mock_request.client = MagicMock(host="192.168.1.1")

        result = get_client_identifier(mock_request)
        assert result == "key:abc123"

    def test_uses_forwarded_for_header(self):
        """Should use X-Forwarded-For if no API key."""
        from app.crosscutting.rate_limit import get_client_identifier

        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No api_key_hash
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        mock_request.client = MagicMock(host="127.0.0.1")

        result = get_client_identifier(mock_request)
        assert result == "ip:10.0.0.1"  # First IP (original client)

    def test_falls_back_to_client_ip(self):
        """Should fall back to client IP if no other identifier."""
        from app.crosscutting.rate_limit import get_client_identifier

        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No api_key_hash
        mock_request.headers = {}  # No X-Forwarded-For
        mock_request.client = MagicMock(host="192.168.1.100")

        result = get_client_identifier(mock_request)
        assert result == "ip:192.168.1.100"


@pytest.mark.unit
class TestRateLimitHelpers:
    """Test rate limit helper functions."""

    def test_is_rate_limiting_enabled_true(self):
        """Should return True when rate limit is configured."""
        from app.crosscutting.rate_limit import is_rate_limiting_enabled

        with patch("app.crosscutting.config.get_settings") as mock_settings:
            mock_settings.return_value.rate_limit_rps = 10.0
            mock_settings.return_value.rate_limit_burst = 20

            assert is_rate_limiting_enabled() is True

    def test_is_rate_limiting_enabled_false_when_rps_zero(self):
        """Should return False when RPS is 0."""
        from app.crosscutting.rate_limit import is_rate_limiting_enabled

        with patch("app.crosscutting.config.get_settings") as mock_settings:
            mock_settings.return_value.rate_limit_rps = 0
            mock_settings.return_value.rate_limit_burst = 20

            assert is_rate_limiting_enabled() is False

    def test_reset_rate_limiter(self):
        """Reset should clear the global limiter."""
        from app.crosscutting.rate_limit import get_rate_limiter, reset_rate_limiter

        with patch("app.crosscutting.config.get_settings") as mock_settings:
            mock_settings.return_value.rate_limit_rps = 10.0
            mock_settings.return_value.rate_limit_burst = 20

            # R: Get limiter and consume a token
            reset_rate_limiter()
            limiter1 = get_rate_limiter()
            limiter1.consume("test")

            # R: Reset and get new limiter
            reset_rate_limiter()
            limiter2 = get_rate_limiter()

            # R: Should be a fresh limiter
            assert limiter2.get_remaining("test") == 20
