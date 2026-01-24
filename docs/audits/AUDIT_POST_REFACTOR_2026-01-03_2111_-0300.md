# Auditoría Post-Refactor — RAG Corp (HISTORICAL)

> HISTORICAL: este reporte incluye versiones de herramientas (ej. `@v4`) sin relacion con el versionado del producto.

**Fecha**: 2026-01-03 21:11:24 -0300  
**Branch**: `main`  
**Commit**: `4fa0ba07cd850b43c68a3588767ca9cf28081984`  
**Working tree**: clean  
**Auditor**: GitHub Copilot (Claude Opus 4.5)

---

## Metadata de Ejecución

```
$ date +"%Y-%m-%d %H:%M:%S %z"
2026-01-03 21:11:24 -0300

$ pwd
/home/santi/dev/rag-corp

$ git rev-parse --show-toplevel
/home/santi/dev/rag-corp

$ git branch --show-current
main

$ git rev-parse HEAD
4fa0ba07cd850b43c68a3588767ca9cf28081984

$ git remote -v
origin	git@github.com:SaintWyss/rag-corp.git (fetch)
origin	git@github.com:SaintWyss/rag-corp.git (push)
```

---

## A) Arquitectura Real (Post-Refactor)

### Componentes Principales

| Componente | Ubicación | Stack | Responsabilidad |
|------------|-----------|-------|-----------------|
| **Frontend** | `apps/frontend/` | Next.js, TypeScript, Tailwind CSS | UI para consultas RAG |
| **Backend** | `apps/backend/` | FastAPI, Python 3.11, psycopg 3.2 | API REST + lógica RAG |
| **Contracts** | `shared/contracts/` | OpenAPI 3.1 + Orval | Single source of truth FE↔BE |
| **Database** | PostgreSQL 16 + pgvector | SQL + Vector | Almacenamiento de documentos y embeddings |
| **Infra** | `infra/` | Docker Compose, Prometheus, Grafana | Orquestación y observabilidad |

### Boundaries (Clean Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (Presentation)                                   │
│  main.py, routes.py, auth.py, rate_limit.py, middleware.py  │
│  error_responses.py (RFC 7807), security.py, versioning.py  │
├─────────────────────────────────────────────────────────────┤
│  Application Layer (Use Cases + Policies)                   │
│  answer_query.py, ingest_document.py, search_chunks.py      │
│  context_builder.py (MAX_CONTEXT policy)                    │
├─────────────────────────────────────────────────────────────┤
│  Domain Layer (Entities + Ports)                            │
│  entities.py, repositories.py (Protocol), services.py       │
│  ✅ CERO imports de FastAPI/psycopg/google                  │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer (Adapters + Decorators)               │
│  postgres_document_repo.py, google_*_service.py             │
│  retry.py (tenacity), pool.py, cache.py                     │
└─────────────────────────────────────────────────────────────┘
```

**Verificación DIP (Dependency Inversion)**:
- `apps/backend/app/domain/*.py`: Solo imports de stdlib (dataclasses, typing, uuid)
- `apps/backend/app/application/*.py`: Solo imports de domain
- ✅ PASS - Boundaries correctamente respetados

### Flujo Principal

**Ingesta** (`POST /v1/ingest/text`):
1. `routes.py` → recibe documento
2. `IngestDocumentUseCase` orquesta:
   - `SimpleTextChunker.chunk()` (900 chars, 120 overlap)
   - `GoogleEmbeddingService.embed_batch()` (768D vectors)
   - `PostgresDocumentRepository.save_chunks()` (atomic insert)
3. Retorna `{document_id, chunks_created}`

**RAG Query** (`POST /v1/ask`):
1. `routes.py` → recibe query + top_k
2. `AnswerQueryUseCase` ejecuta:
   - `GoogleEmbeddingService.embed_query()` con retry
   - `PostgresDocumentRepository.search_similar()` (cosine distance)
   - `ContextBuilder.build()` (MAX_CONTEXT_CHARS=12000)
   - `GoogleLLMService.generate_answer()` con retry
3. Retorna `{answer, sources[], timings{}}`

### Cross-Cutting Concerns

| Concern | Archivo | Estado |
|---------|---------|--------|
| **Auth** | `apps/backend/app/auth.py` | ✅ API Key con scopes |
| **Rate Limit** | `apps/backend/app/rate_limit.py` | ✅ Token Bucket |
| **Metrics** | `apps/backend/app/metrics.py` | ✅ Prometheus `/metrics` |
| **Tracing** | `apps/backend/app/tracing.py` | ✅ OpenTelemetry opcional |
| **Retry** | `apps/backend/app/infrastructure/services/retry.py` | ✅ Tenacity decorator |
| **Logging** | `apps/backend/app/logger.py` | ✅ JSON structured + request_id |
| **Security Headers** | `apps/backend/app/security.py` | ✅ CSP, HSTS, X-Frame |

---

## B) Mapa de Carpetas

### Top-Level

| Carpeta/Archivo | Rol | Por qué existe |
|-----------------|-----|----------------|
| `apps/frontend/` | UI Next.js | Interfaz de usuario SPA |
| `apps/backend/` | API FastAPI | Lógica de negocio RAG |
| `shared/contracts/` | Contratos tipados | OpenAPI → TypeScript (Orval) |
| `infra/` | Infraestructura | Docker configs, Prometheus, Grafana |
| `docs/` | Documentación técnica | Arquitectura, API, runbooks |
| `tests/` | Tests adicionales | k6 load tests |
| `compose.yaml` | Docker dev | PostgreSQL + Backend |
| `compose.prod.yaml` | Docker prod | Con frontend + limits |
| `compose.observability.yaml` | Monitoring stack | Prometheus + Grafana |
| `pnpm-workspace.yaml` | Monorepo config | `frontend`, `shared/*` |
| `turbo.json` | Build pipeline | Tasks: dev, build, lint, test |

### Backend (`apps/backend/app/`)

| Carpeta | Rol | Archivos Clave |
|---------|-----|----------------|
| `domain/` | Core business | `entities.py`, `repositories.py`, `services.py` |
| `application/` | Use cases | `use_cases/answer_query.py`, `context_builder.py` |
| `infrastructure/repositories/` | DB adapters | `postgres_document_repo.py` |
| `infrastructure/services/` | External APIs | `google_embedding_service.py`, `google_llm_service.py`, `retry.py` |
| `infrastructure/text/` | Text processing | `chunker.py`, `semantic_chunker.py` |
| `infrastructure/db/` | DB pool | `pool.py` |
| `infrastructure/cache/` | Caching | `cache.py` (LRU embeddings) |
| `prompts/` | LLM templates | `v1_answer_es.md` |

### Frontend (`apps/frontend/`)

| Carpeta | Rol |
|---------|-----|
| `app/` | Next.js App Router |
| `app/components/` | React components (`QueryForm`, `AnswerCard`) |
| `app/hooks/` | Custom hooks (`useRagAsk.ts` con AbortController) |
| `__tests__/` | Jest + Testing Library |

---

## C) Scorecard (0–100)

| # | Categoría | Score | Evidencia |
|---|-----------|-------|-----------|
| 1 | **Clean Architecture / Boundaries** | 10/10 | Domain/Application sin imports de infra ✅ |
| 2 | **SOLID / Mantenibilidad** | 9/10 | Protocols, DI, SRP. Minor: main.py grande |
| 3 | **Errores / Contratos** | 9/10 | RFC 7807, ErrorCode enum, Pydantic validation |
| 4 | **Seguridad** | 8/10 | Auth, rate limit, headers. Falta: RBAC granular |
| 5 | **Observabilidad** | 9/10 | Logs JSON, Prometheus, Tracing opcional, request_id |
| 6 | **Performance / DB** | 8/10 | Connection pool, batch insert, índice IVF |
| 7 | **Calidad RAG** | 8/10 | Chunking, grounding metadata, prompt versioning |
| 8 | **Tests / CI** | 8/10 | Coverage unit, integration suite, CI workflow |
| 9 | **Docs / Runbooks** | 7/10 | Estructura completa, algunos TODOs pendientes |
| 10 | **DevOps / Deployment** | 7/10 | Compose prod, Dockerfiles. Falta: K8s |

### Total: **83/100**

### Nivel: **Staging-Ready**

### Veredicto: ✅ **READY** (para staging/pre-prod)

---

## D) Top 10 Deuda Técnica (Post-Refactor)

| # | Severidad | Issue | Evidencia | Fix Recomendado |
|---|-----------|-------|-----------|-----------------|
| 1 | MED | `main.py` tiene ~200 líneas | `apps/backend/app/main.py` | Extraer exception handlers |
| 2 | MED | Sin MMR retrieval | `postgres_document_repo.py` | Implementar Maximal Marginal Relevance |
| 3 | MED | Cache solo in-memory | `apps/backend/app/infrastructure/cache.py` | Considerar Redis para prod |
| 4 | LOW | Sin e2e tests | No existe `tests/e2e/` | Agregar Playwright |
| 5 | LOW | Frontend sin coverage threshold | `apps/frontend/jest.config.js` | Agregar threshold 70% |
| 6 | LOW | Health check Google opcional | `apps/backend/app/main.py` | Hacer configurable |
| 7 | LOW | Alembic migrations sin docs | `apps/backend/alembic/` | Documentar proceso |
| 8 | LOW | Observability stack separado | `compose.observability.yaml` | Integrar en prod |
| 9 | LOW | Sin CHANGELOG automatizado | - | Implementar conventional-changelog |
| 10 | LOW | TODOs en docs | Varios archivos | Completar próxima iteración |

---

## E) Checklist "Correr Local"

### Requisitos
- Node.js 20.9+
- pnpm 10+
- Docker + Docker Compose
- Cuenta Google Cloud con Gemini API

### Comandos

```bash
# 1. Clonar y configurar
git clone https://github.com/SaintWyss/rag-corp.git
cd rag-corp
cp .env.example .env
# Editar .env: GOOGLE_API_KEY=<tu-clave>

# 2. Instalar dependencias
pnpm install

# 3. Levantar infraestructura
pnpm docker:up

# 4. Generar contratos
pnpm contracts:export
pnpm contracts:gen

# 5. Desarrollo
pnpm dev
```

### URLs
| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

---

## Docs Update Prompt (copy/paste)

```markdown
@workspace Quiero actualizar TODA la documentación del repo de forma profesional y consistente con el estado ACTUAL del código.

REGLAS
- Permitido: crear/editar archivos .md y README.md.
- NO inventar comandos: extraerlos de package.json scripts, turbo.json, compose.yaml.
- Si falta información, dejar TODO explícito.
- No pegar código largo en el chat.
- Usar rutas reales del repo (NO paths legacy).

ARCHIVOS A GENERAR/ACTUALIZAR

1) docs/README.md - Documentación consolidada + índice completo
2) docs/architecture/overview.md - Diagrama de capas, flujos
3) docs/design/patterns.md - Patrones aplicados (extraer de PATTERN_MAP)
4) docs/api/http-api.md - Endpoints, auth, error catalog completo
5) docs/data/postgres-schema.md - Schema, índices, queries
6) docs/runbook/local-dev.md - Quickstart, env vars, troubleshooting
7) docs/quality/testing.md - Estructura tests, coverage, CI
8) docs/diagrams/*.md - Mermaid: architecture, rag-flow, ingest-flow
9) README.md raíz - Portal con quickstart, estructura, links

PROCESO
1) Escanear package.json scripts, compose.yaml, .env.example
2) Parsear routes.py para endpoints reales
3) Documentar Settings de config.py
4) Referenciar PATTERN_MAP existente
5) Verificar links internos al finalizar
6) Generar docs/archive/runbook/docs-update-report.md

NO HACER
- No inventar endpoints/comandos
- No usar paths legacy
```

---

**Generado**: 2026-01-03 21:11 -0300
