"""
===============================================================================
TARJETA CRC — routes.py (Shim de compatibilidad)
===============================================================================

Responsabilidades:
  - Mantener compatibilidad con app/api/main.py que hace:
      from ..interfaces.api.http.routes import router
  - NO contiene endpoints.
  - Solo re-exporta el router raíz definido en router.py.

Colaboradores:
  - router.py (composición real del router)
===============================================================================
"""

from app.container import (
    get_delete_document_use_case,
    get_get_workspace_use_case,
    get_reprocess_document_use_case,
    get_upload_document_use_case,
)

from .router import router

__all__ = [
    "router",
    "get_delete_document_use_case",
    "get_get_workspace_use_case",
    "get_reprocess_document_use_case",
    "get_upload_document_use_case",
]
