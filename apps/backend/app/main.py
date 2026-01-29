"""
Name: Backend ASGI Entrypoint (app.main)

Responsibilities:
  - Re-export the FastAPI app for ASGI servers and tooling
  - Preserve the import path used by uvicorn/gunicorn and tests
  - Keep this module side-effect free beyond importing app.api.main
  - Define a narrow public surface using __all__
  - Act as the stable handoff from runtime to application wiring

Collaborators:
  - app.api.main: module that constructs and exposes the FastAPI app
  - FastAPI app instance (ASGI callable) consumed by the server
  - ASGI servers (uvicorn, gunicorn) configured to import app.main:app
  - Python import system and module loader

Notes/Constraints:
  - No configuration or IO should live here; keep it thin and predictable
  - Importing this module must not change runtime behavior or env validation
  - Changing this path is a deployment-breaking change for infra scripts
  - Use this module only as an entrypoint, not for business logic
"""

from app.api.main import app

__all__ = ["app"]
