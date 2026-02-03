# Runbook de desarrollo local
Documento operativo para levantar el backend en local.

## Arranque rápido (Docker)
Evidencia de scripts: `package.json`.

```bash
# Stack base (db + migrate + rag-api)
pnpm stack:core

# Migraciones manuales (si hace falta)
pnpm db:migrate

# Bootstrap de admin (opcional)
pnpm admin:bootstrap
```

## Backend sin Docker
Evidencia de entrypoint ASGI: `apps/backend/app/main.py`.

```bash
cd apps/backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Variables mínimas
Fuente de verdad: `apps/backend/app/crosscutting/config.py`.

- `DATABASE_URL` (requerido)
- `GOOGLE_API_KEY` o `FAKE_LLM=1` + `FAKE_EMBEDDINGS=1`
- `REDIS_URL` (si levantás worker)

`.env` es leído por `Settings` (`apps/backend/app/crosscutting/config.py`).

## Export OpenAPI
```bash
cd apps/backend
python scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

## Ver también
- Worker → `docs/runbook/worker.md`
- Testing → `docs/quality/testing.md`
- Configuración → `docs/reference/config.md`
