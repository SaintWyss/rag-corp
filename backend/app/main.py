"""
Name: FastAPI Application Entry Point

Responsibilities:
  - Initialize FastAPI application with metadata (title, version)
  - Configure middleware (CORS, request context)
  - Mount router with RAG endpoints under /v1 prefix
  - Expose health check and metrics endpoints

Collaborators:
  - FastAPI: ASGI web framework
  - CORSMiddleware: Cross-Origin Resource Sharing handler
  - RequestContextMiddleware: Request ID and logging context
  - routes.router: Business logic endpoints (ingest, query, ask)

Constraints:
  - CORS configurable via ALLOWED_ORIGINS env var (comma-separated)
  - No rate limiting or authentication
  - Health check validates DB only (doesn't verify Google API connectivity)

Notes:
  - Middleware order matters: RequestContext → CORS → routes
  - /v1 prefix allows API versioning
  - /healthz follows Kubernetes health check convention
  - /metrics exposes Prometheus metrics

Production Readiness:
  - Env validation enforced at startup (via lifespan, not import time)
  - Request tracing with X-Request-Id header
  - Structured JSON logging with request correlation
"""

import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .auth_routes import router as auth_router
from .logger import logger
from .container import get_document_repository
from .config import get_settings
from .middleware import RequestContextMiddleware, BodyLimitMiddleware
from .rate_limit import RateLimitMiddleware
from .auth import is_auth_enabled
from .rbac import require_metrics_permission
from .versioning import include_versioned_routes
from .infrastructure.db.pool import init_pool, close_pool
from .exception_handlers import register_exception_handlers
from .security import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle. Validates settings and initializes pool."""
    # This will raise ValidationError if env vars are missing/invalid
    settings = get_settings()

    # R: Initialize connection pool
    init_pool(
        database_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )

    logger.info(
        "RAG Corp API starting up",
        extra={
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "otel_enabled": os.getenv("OTEL_ENABLED", "0") == "1",
            "auth_enabled": is_auth_enabled(),
            "rate_limit_rps": settings.rate_limit_rps,
            "db_pool_min": settings.db_pool_min_size,
            "db_pool_max": settings.db_pool_max_size,
        },
    )
    yield

    # R: Close pool on shutdown
    close_pool()
    logger.info("RAG Corp API shutting down")


# R: Get settings for CORS configuration (safe at module level after env is loaded)
def _get_allowed_origins() -> list[str]:
    """Get CORS origins from settings, with fallback for import-time errors."""
    try:
        return get_settings().get_allowed_origins_list()
    except Exception:
        # Fallback for tests that don't set env vars
        return ["http://localhost:3000"]


# R: Create FastAPI application instance with API metadata
app = FastAPI(
    title="RAG Corp API",
    version="0.1.0",
    lifespan=lifespan,
    # R: OpenAPI security scheme for API key authentication
    openapi_tags=[
        {
            "name": "ingest",
            "description": "Document ingestion (requires 'ingest' scope)",
        },
        {
            "name": "query",
            "description": "Semantic search and RAG (requires 'ask' scope)",
        },
        {
            "name": "documents",
            "description": "Document management (requires document permissions)",
        },
        {
            "name": "auth",
            "description": "User authentication (JWT)",
        },
    ],
)

# R: Add security scheme to OpenAPI
app.openapi_schema = None  # Force regeneration


def custom_openapi():
    fastapi_app = globals().get("_fastapi_app") or app
    if fastapi_app.openapi_schema:
        return fastapi_app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=fastapi_app.title,
        version=fastapi_app.version,
        routes=fastapi_app.routes,
    )
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key with appropriate scope (ingest, ask, metrics)",
        }
    }
    # R: Apply security globally (endpoints can override)
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    fastapi_app.openapi_schema = openapi_schema
    return fastapi_app.openapi_schema


app.openapi = custom_openapi

# R: Middleware order (bottom = first to execute):
# 1. RateLimitMiddleware (ASGI) - checks rate before anything
# 2. BodyLimitMiddleware - rejects oversized bodies early
# 3. CORSMiddleware - handles preflight
# 4. RequestContextMiddleware - sets request_id

# R: Add body limit middleware
app.add_middleware(BodyLimitMiddleware)

# R: Add security headers middleware (X-Content-Type-Options, X-Frame-Options, HSTS, CSP)
app.add_middleware(SecurityHeadersMiddleware)

# R: Add request context middleware
app.add_middleware(RequestContextMiddleware)

# R: Configure CORS with secure defaults
_cors_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=_cors_settings.cors_allow_credentials,  # R: Secure default: False
    allow_methods=["GET", "POST", "OPTIONS"],  # R: Only needed methods
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Request-Id",
    ],  # R: Explicit headers
)

# R: Register API routes under /v1 prefix for versioning
app.include_router(router, prefix="/v1")

# R: Register auth routes (no version prefix)
app.include_router(auth_router)

# R: Register versioned routes (v1, v2)
include_versioned_routes(app)

# R: Register exception handlers for structured error responses
register_exception_handlers(app)


# R: Health check endpoint for monitoring/orchestration (Kubernetes, Docker)
@app.get("/healthz")
def healthz(request: Request, full: bool = False):
    """
    R: Enhanced health check that verifies system dependencies.

    Args:
        full: If True, also check Google API connectivity (slower)
              Respects HEALTHCHECK_GOOGLE_ENABLED setting

    Returns:
        ok: True if all checked systems operational
        db: "connected" or "disconnected"
        google: "available", "unavailable", "disabled", or "skipped" (only with full=true)
        request_id: Correlation ID for this request
    """
    settings = get_settings()
    db_status = "disconnected"
    try:
        repo = get_document_repository()
        if repo.ping():
            db_status = "connected"
    except Exception as e:
        logger.warning("Health check: DB unavailable", extra={"error": str(e)})

    result = {
        "ok": db_status == "connected",
        "db": db_status,
        "request_id": getattr(request.state, "request_id", None),
    }

    # R: Full mode: also verify Google API connectivity (if enabled)
    if full:
        if settings.healthcheck_google_enabled:
            google_status = _check_google_api()
            result["google"] = google_status
            # R: Overall health requires all checked services to be OK
            if google_status == "unavailable":
                result["ok"] = False
        else:
            result["google"] = "skipped"

    return result


def _check_google_api() -> str:
    """
    R: Check Google API connectivity with a simple embedding call.

    Returns:
        "available": API is responding
        "unavailable": API is not responding or erroring
        "disabled": No API key configured
    """
    import os

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return "disabled"

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # R: Minimal API call to verify connectivity (cheap operation)
        resp = client.models.embed_content(
            model="text-embedding-004",
            contents=["health check"],
            config={"task_type": "retrieval_query"},
        )

        # R: Verify we got a valid response
        embeddings = resp.embeddings or []
        if embeddings and embeddings[0].values:
            return "available"
        return "unavailable"
    except Exception as e:
        logger.warning("Health check: Google API unavailable", extra={"error": str(e)})
        return "unavailable"


# R: Prometheus metrics endpoint
@app.get("/metrics")
def metrics(_auth: None = Depends(require_metrics_permission())):
    """
    R: Expose Prometheus metrics.

    Returns:
        Prometheus text format metrics
    """
    from .metrics import get_metrics_response, is_prometheus_available

    if not is_prometheus_available():
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain",
        )

    body, content_type = get_metrics_response()
    return Response(content=body, media_type=content_type)


# R: Wrap app with rate limit middleware (ASGI-style)
# This MUST be at the very end, after all FastAPI setup
_fastapi_app = app
app = RateLimitMiddleware(_fastapi_app)
