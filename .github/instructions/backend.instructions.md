---
applyTo: "services/rag-api/**"
---

- Python 3.11 + FastAPI: preferir estructura por módulos claros (routes / services / store / utils).
- Manejo de errores: usar HTTPException y/o exception handlers, sin stack traces crudos.
- Logging: usar `logging` (no `print`).
- Validación: Pydantic para requests/responses.
- Tests: si tocás lógica, agregá tests (pytest). Si no hay tests aún, crear unit tests mínimos.
- No inventar rutas: verificar en `services/rag-api/app/routes.py` y `main.py` (prefijos).
- Comentarios CRC en módulos/clases principales (docstrings).
