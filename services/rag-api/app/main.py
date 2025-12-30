"""
Name: FastAPI Application Entry Point

Responsibilities:
  - Initialize FastAPI application with metadata (title, version)
  - Configure CORS middleware for local development
  - Mount router with RAG endpoints under /v1 prefix
  - Expose health check endpoint for monitoring

Collaborators:
  - FastAPI: ASGI web framework
  - CORSMiddleware: Cross-Origin Resource Sharing handler
  - routes.router: Business logic endpoints (ingest, query, ask)

Constraints:
  - CORS hardcoded to localhost:3000 (change to env var for production)
  - No rate limiting or authentication
  - Simplified health check (doesn't verify DB or Google API connectivity)

Notes:
  - allow_credentials=True enables cookie sending (not currently used)
  - /v1 prefix allows API versioning
  - /healthz follows Kubernetes health check convention

Production Readiness:
  - TODO: Read ALLOWED_ORIGINS from .env (Issue #4 tech debt)
  - TODO: Add authentication middleware (API Key or JWT)
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .logger import logger
from .exceptions import RAGError, DatabaseError, EmbeddingError, LLMError
from .store import Store

# R: Create FastAPI application instance with API metadata
app = FastAPI(title="RAG Corp API", version="0.1.0")

# R: Configure CORS for development (allows frontend at localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # R: Allowed origins for CORS
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
    logger.error(f"Database error: {exc.message} | error_id={exc.error_id} | path={request.url.path}")
    return JSONResponse(
        status_code=503,
        content=exc.to_response().to_dict(),
    )


@app.exception_handler(EmbeddingError)
async def embedding_error_handler(request: Request, exc: EmbeddingError):
    """Handle embedding service errors."""
    logger.error(f"Embedding error: {exc.message} | error_id={exc.error_id} | path={request.url.path}")
    return JSONResponse(
        status_code=503,
        content=exc.to_response().to_dict(),
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """Handle LLM service errors."""
    logger.error(f"LLM error: {exc.message} | error_id={exc.error_id} | path={request.url.path}")
    return JSONResponse(
        status_code=503,
        content=exc.to_response().to_dict(),
    )


@app.exception_handler(RAGError)
async def rag_error_handler(request: Request, exc: RAGError):
    """Handle generic RAG errors."""
    logger.error(f"RAG error: {exc.message} | error_id={exc.error_id} | path={request.url.path}")
    return JSONResponse(
        status_code=500,
        content=exc.to_response().to_dict(),
    )


# R: Health check endpoint for monitoring/orchestration (Kubernetes, Docker)
@app.get("/healthz")
def healthz():
    """
    R: Enhanced health check that verifies database connectivity.

    Returns:
        ok: True if all systems operational
        db: "connected" or "disconnected"
    """
    db_status = "disconnected"
    try:
        store = Store()
        with store._conn() as conn:
            conn.execute("SELECT 1")
        db_status = "connected"
        logger.info(f"Health check passed | db={db_status}")
    except Exception as e:
        logger.warning(f"Health check: DB unavailable - {e}")

    return {
        "ok": db_status == "connected",
        "db": db_status,
    }
