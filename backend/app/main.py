"""
Main entry point for the RAG Corp API.

This module re-exports the FastAPI application from app.api.main
to maintain compatibility with the expected module structure.
"""

from app.api.main import app

__all__ = ["app"]
