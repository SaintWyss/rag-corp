"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/__init__.py
===============================================================================

Name:
    Routers Package (HTTP)

Responsibilities:
    - Exponer routers segmentados por bounded context para ser incluidos por el
      router principal.
    - Mantener importaciones limpias y explícitas.

Collaborators:
    - routers.workspaces
    - routers.documents
    - routers.query
    - routers.admin

Notas:
    - Este archivo NO define endpoints. Solo re-exporta routers.
===============================================================================
"""

from .admin import router as admin_router
from .documents import router as documents_router
from .query import router as query_router
from .workspaces import router as workspaces_router

__all__ = [
    "admin_router",
    "documents_router",
    "query_router",
    "workspaces_router",
]
