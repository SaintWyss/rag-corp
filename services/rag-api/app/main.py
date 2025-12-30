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
  - TODO: Add detailed health check (verify DB + Google API)
  - TODO: Add authentication middleware (API Key or JWT)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

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

# R: Health check endpoint for monitoring/orchestration (Kubernetes, Docker)
@app.get("/healthz")
def healthz():
    return {"ok": True}
