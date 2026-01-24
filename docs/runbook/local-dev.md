# Local Development Runbook (v6)

**Project:** RAG Corp
**Last Updated:** 2026-01-22

---

## Quickstart

```bash
cp .env.example .env
pnpm install
pnpm docker:up
pnpm db:migrate
pnpm admin:bootstrap -- --email <ADMIN_EMAIL> --password <ADMIN_PASSWORD>
pnpm dev
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

**Admin (Auto-Seed):**
Para crear automáticamente un admin al levantar el backend (solo local):
`DEV_SEED_ADMIN=1` -> Crea user `admin@local` / `admin`.
NO usar en producción (el backend fallará al inicio por seguridad).

---

## Docker Compose perfiles

- Base: `db`, `rag-api` (default)
- Worker: `--profile worker`
- Storage (MinIO): `--profile storage`
- Observability (Prometheus/Grafana): `--profile observability`
- E2E web: `--profile e2e`

Stack completo:

```bash
pnpm stack:full
pnpm db:migrate
```

---

## Backend (sin Docker)

```bash
cd apps/backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Si no hay Google API key:

```bash
export FAKE_LLM=1 FAKE_EMBEDDINGS=1
```

Export OpenAPI local:

```bash
python3 scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

---

## Frontend (Next.js)

```bash
cd apps/frontend
pnpm dev
```

---

## Environment variables (minimo viable)

Consultar `.env.example` para la lista completa. En local:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
GOOGLE_API_KEY=...
FAKE_LLM=1
FAKE_EMBEDDINGS=1
NEXT_PUBLIC_API_URL=http://localhost:8000
API_KEYS_CONFIG=
RBAC_CONFIG=
```

Para MinIO (profile `storage`):

```
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=rag-documents
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

---

## Testing (local)

```bash
pnpm test:backend:unit
pnpm e2e
```

Ver `docs/quality/testing.md` y `tests/e2e/README.md` para opciones avanzadas.

---

## Observability

Ver `docs/runbook/observability.md` para perfiles compose y endpoints (`/healthz`, `/readyz`, `/metrics`).

