"""
===============================================================================
TARJETA CRC — app/main.py (Entrypoint ASGI)
===============================================================================

Responsabilidades:
  - Exponer el objeto FastAPI `app` para servidores ASGI (uvicorn/gunicorn).
  - Mantener un punto de importación estable y mínimo: "app.main:app".
  - Evitar side-effects: este módulo NO valida env, NO hace IO, NO configura nada.

Colaboradores:
  - app.api.main: compone y expone la instancia de FastAPI.

Patrones aplicados:
  - Facade / Re-export: módulo fino que re-exporta el entrypoint real.

Notas:
  - Cambiar este path rompe despliegues/scripts que importan "app.main:app".
===============================================================================
"""

from app.api.main import app

__all__ = ["app"]
