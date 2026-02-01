"""
===============================================================================
TARJETA CRC — app/api/versioning.py (Alias de Rutas)
===============================================================================

Responsabilidades:
  - Exponer alias de rutas para compatibilidad operativa (sin duplicar lógica).
  - Evitar acoplar routers de negocio a múltiples prefijos.

Patrones aplicados:
  - Router Composition: reutiliza el mismo router bajo diferentes prefijos.
  - Backward-compatible alias: permite migraciones de clientes sin roturas.

Colaboradores:
  - interfaces.api.http.routes.router (router de negocio)
===============================================================================
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from ..interfaces.api.http.routes import router as business_router


def include_versioned_routes(app: FastAPI) -> None:
    """
    Incluye alias de rutas.

    Actualmente:
      - /api/v1 -> apunta al mismo router que /v1
    """
    api_router = APIRouter(prefix="/api")

    # Alias /api/v1/...
    api_router.include_router(business_router, prefix="/v1")

    app.include_router(api_router)


__all__ = ["include_versioned_routes"]
