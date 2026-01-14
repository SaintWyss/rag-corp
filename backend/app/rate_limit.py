"""
Name: Token Bucket Rate Limiter

Responsibilities:
  - Limit requests per API key (or IP as fallback)
  - Token bucket algorithm for smooth rate limiting
  - Return 429 with Retry-After header when rate exceeded
  - Log rate limit events (with key hash, not raw key)

Collaborators:
  - config.py: RATE_LIMIT_RPS, RATE_LIMIT_BURST settings
  - middleware.py: Applied as middleware
  - auth.py: Uses key hash from request.state

Constraints:
  - In-memory storage (resets on restart, no persistence)
  - Thread-safe (using locks)
  - No external dependencies

Notes:
  - Token bucket allows controlled bursts while maintaining average rate
  - Tokens refill at RPS rate up to BURST maximum
  - Each request consumes 1 token
"""

import time
import threading
from dataclasses import dataclass
from typing import Optional

from .error_responses import app_exception_handler, rate_limited
from .logger import logger


@dataclass
class Bucket:
    """R: Token bucket state for a single key/IP."""

    tokens: float
    last_refill: float


class TokenBucket:
    """
    R: Token bucket rate limiter.

    Algorithm:
      1. Each key has a bucket with up to `burst` tokens
      2. Tokens refill at `rps` tokens/second
      3. Request consumes 1 token
      4. If no tokens, request is rejected

    Attributes:
        rps: Refill rate (tokens per second)
        burst: Maximum tokens (bucket capacity)
    """

    def __init__(self, rps: float, burst: int):
        if rps <= 0:
            raise ValueError("rps must be positive")
        if burst <= 0:
            raise ValueError("burst must be positive")

        self.rps = rps
        self.burst = burst
        self._buckets: dict[str, Bucket] = {}
        self._lock = threading.Lock()

    def _get_or_create_bucket(self, key: str) -> Bucket:
        """R: Get bucket for key, creating if needed."""
        if key not in self._buckets:
            self._buckets[key] = Bucket(
                tokens=float(self.burst),
                last_refill=time.monotonic(),
            )
        return self._buckets[key]

    def _refill(self, bucket: Bucket, now: float) -> None:
        """R: Refill tokens based on elapsed time."""
        elapsed = now - bucket.last_refill
        refill_amount = elapsed * self.rps
        bucket.tokens = min(self.burst, bucket.tokens + refill_amount)
        bucket.last_refill = now

    def consume(self, key: str) -> tuple[bool, float]:
        """
        R: Try to consume one token from the bucket.

        Args:
            key: Identifier (API key hash or IP address)

        Returns:
            (allowed, retry_after_seconds)
            - allowed: True if request should proceed
            - retry_after: Seconds until a token is available (0 if allowed)
        """
        with self._lock:
            now = time.monotonic()
            bucket = self._get_or_create_bucket(key)
            self._refill(bucket, now)

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return (True, 0.0)
            else:
                # R: Calculate time until next token
                tokens_needed = 1 - bucket.tokens
                retry_after = tokens_needed / self.rps
                return (False, retry_after)

    def get_remaining(self, key: str) -> int:
        """R: Get remaining tokens for a key (for headers)."""
        with self._lock:
            if key not in self._buckets:
                return self.burst
            bucket = self._buckets[key]
            now = time.monotonic()
            self._refill(bucket, now)
            return int(bucket.tokens)

    def clear(self) -> None:
        """R: Clear all buckets (for testing)."""
        with self._lock:
            self._buckets.clear()


# R: Global rate limiter instance (lazy initialization)
_rate_limiter: Optional[TokenBucket] = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> TokenBucket:
    """R: Get or create global rate limiter."""
    global _rate_limiter

    with _limiter_lock:
        if _rate_limiter is None:
            from .config import get_settings

            settings = get_settings()
            _rate_limiter = TokenBucket(
                rps=settings.rate_limit_rps,
                burst=settings.rate_limit_burst,
            )
        return _rate_limiter


def reset_rate_limiter() -> None:
    """R: Reset rate limiter (for testing)."""
    global _rate_limiter
    with _limiter_lock:
        _rate_limiter = None


def is_rate_limiting_enabled() -> bool:
    """R: Check if rate limiting is configured."""
    from .config import get_settings

    settings = get_settings()
    return settings.rate_limit_rps > 0 and settings.rate_limit_burst > 0


def get_client_identifier(request) -> str:
    """
    R: Get identifier for rate limiting.

    Priority:
      1. API key hash (if authenticated)
      2. X-Forwarded-For header (if behind proxy)
      3. Client IP address
    """
    # R: Prefer API key hash (set by auth middleware)
    if hasattr(request.state, "api_key_hash"):
        return f"key:{request.state.api_key_hash}"

    # R: Try X-Forwarded-For (for proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # R: Take first IP (original client)
        ip = forwarded_for.split(",")[0].strip()
        return f"ip:{ip}"

    # R: Fall back to direct client IP
    client = request.client
    if client:
        return f"ip:{client.host}"

    return "ip:unknown"


class RateLimitMiddleware:
    """
    R: ASGI middleware for rate limiting.

    Applies token bucket rate limiting per client.
    Skips rate limiting for healthz endpoint.
    """

    # R: Paths excluded from rate limiting
    EXCLUDED_PATHS = {"/healthz", "/metrics", "/openapi.json", "/docs", "/redoc"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # R: Skip rate limiting if disabled
        if not is_rate_limiting_enabled():
            await self.app(scope, receive, send)
            return

        # R: Skip excluded paths
        path = scope.get("path", "")
        if path in self.EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        # R: Build minimal request-like object for identifier
        from starlette.requests import Request

        request = Request(scope, receive, send)

        client_id = get_client_identifier(request)
        limiter = get_rate_limiter()
        allowed, retry_after = limiter.consume(client_id)

        if not allowed:
            # R: Log rate limit event
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "path": path,
                    "retry_after": round(retry_after, 2),
                },
            )

            # R: Send 429 response (RFC 7807)
            retry_after_int = max(1, int(retry_after) + 1)
            exc = rate_limited(retry_after_int)
            headers = getattr(exc, "headers", None) or {}
            headers.update(
                {
                    "x-ratelimit-remaining": "0",
                    "x-ratelimit-limit": str(limiter.burst),
                }
            )
            exc.headers = headers
            response = await app_exception_handler(request, exc)
            await response(scope, receive, send)
            return

        # R: Add rate limit headers to response
        remaining = limiter.get_remaining(client_id)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-ratelimit-remaining", str(remaining).encode()))
                headers.append((b"x-ratelimit-limit", str(limiter.burst).encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
