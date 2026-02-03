# RAG Corp v6

Sistema de **Retrieval-Augmented Generation (RAG)** empresarial para ingestar documentos, buscarlos semanticamente y responder con fuentes citadas. La unidad tecnica de scoping es el **Workspace** ("Seccion" solo si el copy UI lo requiere).

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)

---

## Estado v6 (resumen)

- **Workspace-first**: CRUD y visibilidad `PRIVATE | ORG_READ | SHARED` con `workspace_acl`.
- **Scoping total**: documentos, chunks, retrieval y ask siempre por `workspace_id`.
- **Async upload**: S3/MinIO + worker (Redis/RQ) con estados `PENDING/PROCESSING/READY/FAILED`.
- **Auth dual**: JWT (usuarios) + `X-API-Key` (servicios) con RBAC opcional.
- **Observabilidad**: `/healthz`, `/readyz`, `/metrics` (auth en prod) y stack Prometheus/Grafana opcional.
- **Contratos**: OpenAPI exportado desde el backend y cliente TS generado.

---

## Quickstart local (v6)

### Requisitos

- Docker + Docker Compose v2
- Node.js 20.x + pnpm 10.x
- Google Gemini API key (o FAKE_LLM/FAKE_EMBEDDINGS)

### Configuracion

```bash
cp .env.example .env
```

Editar `.env` con valores minimos:

- `DATABASE_URL`
- `GOOGLE_API_KEY` (o `FAKE_LLM=1` y `FAKE_EMBEDDINGS=1`)

### Levantar stack basico (db + api)

```bash
pnpm install
pnpm docker:up
pnpm db:migrate
pnpm admin:bootstrap -- --email "<ADMIN_EMAIL>" --password "<ADMIN_PASSWORD>"
```

### Stack completo (worker + storage)

```bash
export S3_ENDPOINT_URL=http://minio:9000
export S3_BUCKET=<S3_BUCKET>
export S3_ACCESS_KEY=<S3_ACCESS_KEY>
export S3_SECRET_KEY=<S3_SECRET_KEY>

pnpm stack:full
pnpm db:migrate
```

### Frontend (dev)

```bash
pnpm dev
```

### Contratos (OpenAPI -> TS)

```bash
pnpm contracts:export
pnpm contracts:gen
```

---

## Endpoints canónicos

- **Canonical**: `/v1/workspaces/{workspace_id}/...`
- **Alias versionado**: `/api/v1/...` (mismo contrato)
- **Legacy** (DEPRECATED): `/v1/documents`, `/v1/ask`, `/v1/query`, `/v1/ingest/*` con `workspace_id` obligatorio

Ver `docs/reference/api/http-api.md` y `shared/contracts/openapi.json`.

---

## Hardening (produccion)

Fail-fast en `APP_ENV=production` (ver `apps/backend/app/crosscutting/config.py`):

- `JWT_SECRET` fuerte (>=32 chars) y no default
- `JWT_COOKIE_SECURE=true`
- `METRICS_REQUIRE_AUTH=true`
- `API_KEYS_CONFIG` o `RBAC_CONFIG` presentes (protege `/metrics`)
- CSP sin `unsafe-inline` (ver `apps/backend/app/crosscutting/security.py`)

Runbooks: `docs/security/production-hardening.md` y `docs/runbook/observability.md`.

---

## Scripts utiles

| Script                      | Uso                               |
| --------------------------- | --------------------------------- |
| `pnpm dev`                  | Dev server (turbo)                |
| `pnpm docker:up`            | db + rag-api                      |
| `pnpm stack:full`           | db + api + redis + worker + minio |
| `pnpm docker:observability` | Prometheus + Grafana              |
| `pnpm db:migrate`           | Alembic upgrade head              |
| `pnpm admin:bootstrap`      | Crear admin JWT                   |
| `pnpm contracts:export`     | Export OpenAPI                    |
| `pnpm contracts:gen`        | Generar cliente TS                |
| `pnpm test:backend:unit`    | Tests unit backend (Docker)       |
| `pnpm e2e`                  | Playwright                        |

---

## Documentacion v6 (portal)

- `docs/README.md` (indice)
- Arquitectura: `docs/architecture/overview.md`
- ADRs: `docs/architecture/adr/`
- API: `docs/reference/api/http-api.md`
- DB: `docs/reference/data/postgres-schema.md`
- Runbooks: `docs/runbook/`
- Testing: `docs/quality/testing.md`
- Informe definitivo v6: `docs/project/informe_de_sistemas_rag_corp.md`

---

## Versionado

- **v6**: version actual del sistema y la documentacion.
- **HISTORICAL v4**: especificacion de origen y reportes historicos (`TODO(verify)`).

---

## Licencia

Proprietary — personal/educational evaluation only. Commercial use and redistribution prohibited.
