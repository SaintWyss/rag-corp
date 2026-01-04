"""
Name: Retry Helper with Exponential Backoff + Jitter

Responsibilities:
  - Classify transient vs permanent errors (HTTP codes, exceptions)
  - Provide tenacity-based retry decorator for Google API calls
  - Apply exponential backoff with jitter to prevent thundering herd
  - Log retry attempts with request_id for observability

Collaborators:
  - tenacity: Retry library with configurable strategies
  - config.Settings: Retry configuration (max_attempts, delays)
  - logger: Structured logging with request correlation

Constraints:
  - Only retry transient errors (429, 5xx, timeouts, connection errors)
  - Never retry permanent errors (400, 401, 403)
  - Jitter prevents synchronized retries across instances

Notes:
  - Based on Google Cloud best practices for retry
  - Exponential backoff: delay = min(base * 2^attempt, max_delay)
  - Jitter: random factor [0.5, 1.5] applied to delay
"""

from functools import wraps
from typing import Callable

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception,
    RetryCallState,
)

from ...logger import logger
from ...config import get_settings


# R: HTTP status codes that indicate transient errors (retry-able)
TRANSIENT_HTTP_CODES: frozenset[int] = frozenset(
    {
        429,  # Too Many Requests (rate limit)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }
)

# R: HTTP status codes that indicate permanent errors (no retry)
PERMANENT_HTTP_CODES: frozenset[int] = frozenset(
    {
        400,  # Bad Request
        401,  # Unauthorized
        403,  # Forbidden
        404,  # Not Found
    }
)


def get_http_status_code(exception: BaseException) -> int | None:
    """
    R: Extract HTTP status code from various exception types.

    Supports google.api_core exceptions and httpx responses.

    Returns:
        HTTP status code if found, None otherwise
    """
    # Google API Core exceptions (google.api_core.exceptions.*)
    if hasattr(exception, "code"):
        code = exception.code
        # Handle gRPC status codes vs HTTP codes
        if isinstance(code, int) and code >= 100:
            return code

    # httpx.HTTPStatusError
    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        return exception.response.status_code

    # google-generativeai specific exceptions
    if hasattr(exception, "status_code"):
        return exception.status_code

    return None


def is_transient_error(exception: BaseException) -> bool:
    """
    R: Determine if an exception is transient (should retry).

    Transient errors include:
      - HTTP 429, 5xx
      - Connection/timeout errors
      - Temporary API unavailability

    Permanent errors (no retry):
      - HTTP 400, 401, 403, 404
      - Invalid API key
      - Malformed requests

    Args:
        exception: The exception to classify

    Returns:
        True if transient (retry), False if permanent (fail fast)
    """
    # R: Check for HTTP status codes
    status_code = get_http_status_code(exception)
    if status_code is not None:
        if status_code in PERMANENT_HTTP_CODES:
            return False
        if status_code in TRANSIENT_HTTP_CODES:
            return True

    # R: Common transient exception types (connection errors, timeouts)
    exception_name = type(exception).__name__.lower()
    transient_patterns = (
        "timeout",
        "connection",
        "temporary",
        "unavailable",
        "resourceexhausted",
        "deadline",
        "aborted",
        "cancelled",
    )

    if any(pattern in exception_name for pattern in transient_patterns):
        return True

    # R: Check exception message for transient indicators
    message = str(exception).lower()
    transient_message_patterns = (
        "rate limit",
        "too many requests",
        "quota exceeded",
        "temporarily unavailable",
        "connection reset",
        "connection refused",
        "timed out",
        "deadline exceeded",
    )

    if any(pattern in message for pattern in transient_message_patterns):
        return True

    # R: Default: treat unknown errors as non-transient (fail fast)
    return False


def _log_retry(retry_state: RetryCallState) -> None:
    """
    R: Log retry attempts with context for observability.

    Called before each retry to record:
      - Function name
      - Attempt number
      - Wait time before next attempt
      - Last exception
    """
    fn_name = getattr(retry_state.fn, "__name__", "unknown")
    attempt = retry_state.attempt_number
    wait_time = retry_state.next_action.sleep if retry_state.next_action else 0
    exc = retry_state.outcome.exception() if retry_state.outcome else None

    logger.warning(
        f"Retry attempt {attempt} for {fn_name}",
        extra={
            "function": fn_name,
            "attempt": attempt,
            "wait_seconds": round(wait_time, 2),
            "error": str(exc) if exc else None,
            "error_type": type(exc).__name__ if exc else None,
        },
    )


def create_retry_decorator(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> Callable:
    """
    R: Create a retry decorator with exponential backoff + jitter.

    Uses settings from config unless overridden. Applies:
      - Exponential backoff: delay doubles each attempt
      - Jitter: randomizes delay to prevent thundering herd
      - Transient error filtering: only retries appropriate errors

    Args:
        max_attempts: Max retry attempts (default from settings)
        base_delay: Initial delay in seconds (default from settings)
        max_delay: Maximum delay cap in seconds (default from settings)

    Returns:
        Configured tenacity retry decorator
    """
    settings = get_settings()

    _max_attempts = max_attempts or settings.retry_max_attempts
    _base_delay = base_delay or settings.retry_base_delay_seconds
    _max_delay = max_delay or settings.retry_max_delay_seconds

    return retry(
        stop=stop_after_attempt(_max_attempts),
        wait=wait_exponential_jitter(
            initial=_base_delay,
            max=_max_delay,
            jitter=_base_delay,  # R: Jitter up to base_delay seconds
        ),
        retry=retry_if_exception(is_transient_error),
        before_sleep=_log_retry,
        reraise=True,  # R: Re-raise last exception after all retries exhausted
    )


def with_retry(func: Callable) -> Callable:
    """
    R: Decorator that applies retry with default settings.

    Convenience wrapper around create_retry_decorator() using
    settings from config.

    Usage:
        @with_retry
        def call_external_api():
            ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # R: Create decorator at call time to pick up current settings
        decorator = create_retry_decorator()
        return decorator(func)(*args, **kwargs)

    return wrapper
