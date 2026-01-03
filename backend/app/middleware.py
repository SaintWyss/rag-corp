"""
Name: HTTP Middleware

Responsibilities:
  - Generate and propagate request_id (UUID)
  - Set request context for logging
  - Add X-Request-Id response header
  - Record request metrics (latency, count)

Collaborators:
  - context.py: ContextVars for request-scoped data
  - metrics.py: Prometheus counters and histograms
  - logger.py: Structured logging

Constraints:
  - Must be first middleware (before CORS, auth, etc.)
  - Must clear context after response

Notes:
  - Uses Starlette middleware pattern (ASGI)
  - request_id is UUID4 for uniqueness
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import (
    request_id_var,
    http_method_var,
    http_path_var,
    clear_context,
)
from .logger import logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    R: Middleware that establishes request context and records metrics.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # R: Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # R: Set context vars for this request
        request_id_var.set(request_id)
        http_method_var.set(request.method)
        http_path_var.set(request.url.path)
        
        # R: Also store in request.state for handlers that need it
        request.state.request_id = request_id
        
        # R: Record start time for latency
        start_time = time.perf_counter()
        
        try:
            # R: Process request
            response = await call_next(request)
            
            # R: Calculate latency
            latency_seconds = time.perf_counter() - start_time
            
            # R: Add request_id to response headers
            response.headers["X-Request-Id"] = request_id
            
            # R: Log request completion
            logger.info(
                "request completed",
                extra={
                    "status_code": response.status_code,
                    "latency_ms": round(latency_seconds * 1000, 2),
                }
            )
            
            # R: Record metrics (imported lazily to avoid circular imports)
            try:
                from .metrics import record_request_metrics
                record_request_metrics(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    latency_seconds=latency_seconds,
                )
            except ImportError:
                pass  # Metrics module not available
            
            return response
            
        except Exception as exc:
            # R: Log error with context
            latency_seconds = time.perf_counter() - start_time
            logger.exception(
                "request failed",
                extra={
                    "latency_ms": round(latency_seconds * 1000, 2),
                    "error": str(exc),
                }
            )
            raise
            
        finally:
            # R: Clear context to prevent leaks
            clear_context()
