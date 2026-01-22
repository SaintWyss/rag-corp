"""
Name: API Versioning

Responsibilities:
  - Provide versioned API routes
  - Support multiple API versions concurrently
  - Enable gradual migration

Notes:
  - v1: Current stable API
  - v2: Future enhancements (placeholder)
"""

from fastapi import APIRouter

from .routes import router as v1_router

# Version 1 - Current stable
api_v1 = APIRouter(prefix="/api/v1", tags=["v1"])
api_v1.include_router(v1_router)

# Version 2 - Future (placeholder)
api_v2 = APIRouter(prefix="/api/v2", tags=["v2"])


def include_versioned_routes(app):
    """Register all versioned routes with the app."""
    app.include_router(api_v1)
    app.include_router(api_v2)
