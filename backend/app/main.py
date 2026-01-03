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
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .logger import logger
from .exceptions import RAGError, DatabaseError, EmbeddingError, LLMError
from .container import get_document_repository
from .config import get_settings
from .middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle. Validates settings at startup."""
    # This will raise ValidationError if env vars are missing/invalid
    settings = get_settings()
    logger.info(
        "RAG Corp API starting up",
        extra={
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "otel_enabled": os.getenv("OTEL_ENABLED", "0") == "1",
        }
    )
    yield
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
app = FastAPI(title="RAG Corp API", version="0.1.0", lifespan=lifespan)

# R: Add request context middleware FIRST (before CORS)
app.add_middleware(RequestContextMiddleware)

# R: Configure CORS for development (allows frontend at localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),  # R: Allowed origins from Settings
    allow_credentials=True,  # R: Allow cookies/auth headers
    allow_methods=["*"],  # R: Allow all HTTP methods
    allow_headers=["*"],  # R: Allow all headers
)

# R: Register API routes under /v1 prefix for versioning
app.include_router(router, prefix="/v1")


# R: Exception handlers for structured error responses
@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors with structured response."""
    logger.error(
        "Database error",
        extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    return JSONResponse(
        status_code=503,
        content=exc.to_response().to_dict(),
    )


@app.exception_handler(EmbeddingError)
async def embedding_error_handler(request: Request, exc: EmbeddingError):
    """Handle embedding service errors."""
    logger.error(
        "Embedding error",
        extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    return JSONResponse(
        status_code=503,
        content=exc.to_response().to_dict(),
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """Handle LLM service errors."""
    logger.error(
        "LLM error",
        extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    return JSONResponse(
        status_code=503,
        content=exc.to_response().to_dict(),
    )


@app.exception_handler(RAGError)
async def rag_error_handler(request: Request, exc: RAGError):
    """Handle generic RAG errors."""
    logger.error(
        "RAG error",
        extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    return JSONResponse(
        status_code=500,
        content=exc.to_response().to_dict(),
    )


# R: Health check endpoint for monitoring/orchestration (Kubernetes, Docker)
@app.get("/healthz")
def healthz(request: Request):
    """
    R: Enhanced health check that verifies database connectivity.

    Returns:
        ok: True if all systems operational
        db: "connected" or "disconnected"
        request_id: Correlation ID for this request
    """
    db_status = "disconnected"
    try:
        repo = get_document_repository()
        if repo.ping():
            db_status = "connected"
    except Exception as e:
        logger.warning("Health check: DB unavailable", extra={"error": str(e)})

    return {
        "ok": db_status == "connected",
        "db": db_status,
        "request_id": getattr(request.state, "request_id", None),
    }


# R: Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
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
