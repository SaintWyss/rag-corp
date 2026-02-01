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

from .router import router

__all__ = ["router"]
