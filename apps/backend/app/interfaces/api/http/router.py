"""
===============================================================================
TARJETA CRC — router.py (Router raíz / Composición)
===============================================================================

Responsabilidades:
  - Definir el APIRouter raíz que se incluye en FastAPI (app.include_router).
  - Centralizar responses RFC7807 para OpenAPI.
  - Componer routers por bounded context (workspaces/documents/query/admin).

Patrones aplicados:
  - Composition over inheritance: router raíz compone sub-routers.
  - Feature-based modular routing: evita routes.py monolítico.
  - Factory: build_router() para testear composición y evitar side-effects al importar.

Colaboradores:
  - crosscutting.error_responses.OPENAPI_ERROR_RESPONSES
  - routers.* (sub-routers por feature)

Notas:
  - Este router se incluye desde app/api/main.py con prefix="/v1".
===============================================================================
"""

from __future__ import annotations

from fastapi import APIRouter

from ....crosscutting.error_responses import OPENAPI_ERROR_RESPONSES
from .routers.admin import router as admin_router
from .routers.documents import router as documents_router
from .routers.query import router as query_router
from .routers.workspaces import router as workspaces_router


def build_router() -> APIRouter:
    """
    Construye el router raíz v1.

    Motivo:
      - Facilita tests (se puede invocar build_router() y verificar que incluye todo).
      - Reduce efectos colaterales al importar módulos (import-time side effects).
    """
    api_router = APIRouter(responses=OPENAPI_ERROR_RESPONSES)

    # Orden recomendado: core primero, admin al final.
    api_router.include_router(workspaces_router)
    api_router.include_router(documents_router)
    api_router.include_router(query_router)
    api_router.include_router(admin_router)

    return api_router


# Alias para mantener compatibilidad con imports existentes:
# from app.interfaces.api.http.router import router
router = build_router()

__all__ = ["router", "build_router"]
