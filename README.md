# RAG Corp

Sistema de **Retrieval-Augmented Generation** (RAG) empresarial que permite ingestar documentos, buscarlos semánticamente y obtener respuestas contextuales generadas por LLM. Resuelve el problema de documentación dispersa: consultas en lenguaje natural con respuestas precisas y fuentes citadas, sin enviar documentos completos a APIs externas.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)

---

## Features

- ✅ Ingesta de documentos vía API REST (`POST /v1/ingest/text`, `/v1/ingest/batch`)
- ✅ Chunking inteligente con límites naturales (900 chars, 120 overlap)
- ✅ Embeddings 768D con Google text-embedding-004
- ✅ Búsqueda vectorial con PostgreSQL + pgvector (índice IVFFlat)
- ✅ Generación RAG con Gemini 1.5 Flash y prompts versionados
- ✅ UI en Next.js con App Router y Tailwind CSS
- ✅ Contratos tipados (OpenAPI → TypeScript vía Orval)
- ✅ Clean Architecture (Domain/Application/Infrastructure)
- ✅ Autenticación por API Key con scopes
- ✅ Rate limiting configurable (token bucket)
- ✅ Métricas Prometheus en `/metrics`
- ✅ Logging estructurado JSON con request_id

---

## Arquitectura

### Componentes

| Componente | Tecnología | Ubicación |
|------------|------------|-----------|
| **Backend** | FastAPI + Python 3.11 | `backend/` |
| **Base de Datos** | PostgreSQL 16 + pgvector 0.8.1 | `infra/postgres/` |
| **Frontend** | Next.js 16 + TypeScript | `frontend/` |
| **Contracts** | OpenAPI 3.1 + Orval | `shared/contracts/` |
| **Embeddings/LLM** | Google Gemini API | Servicios externos |

### Flujo "Ask" (consulta RAG)

```
1. Usuario envía query → Frontend (useRagAsk hook)
2. Frontend llama POST /v1/ask → Backend (routes.py)
3. AnswerQueryUseCase embebe la query → GoogleEmbeddingService
4. Búsqueda vectorial top-k → PostgresDocumentRepository
5. ContextBuilder arma contexto con chunks recuperados
6. GoogleLLMService genera respuesta grounded en contexto
7. Response con answer + sources → Usuario
```

### Flujo "Ingest" (ingesta de documentos)

```
1. Cliente envía documento → POST /v1/ingest/text
2. IngestDocumentUseCase valida y chunkea → SimpleTextChunker
3. GoogleEmbeddingService genera embeddings por chunk
4. PostgresDocumentRepository guarda documento + chunks (transacción atómica)
5. Response con document_id + chunks_created → Cliente
```

---

## Stack

| Capa | Tecnología |
|------|------------|
| API | FastAPI, Pydantic, psycopg 3.2 |
| DB | PostgreSQL 16, pgvector 0.8.1 |
| AI | Google Gemini (text-embedding-004, Gemini 1.5 Flash) |
| Frontend | Next.js 16, TypeScript 5, Tailwind CSS 4 |
| Contracts | OpenAPI 3.1, Orval |
| DevOps | Docker Compose, pnpm, Turbo |

---

## Quickstart Local

### Requisitos

- Docker + Docker Compose
- Node.js 20.9+ y pnpm 10+
- Cuenta Google Cloud con Gemini API habilitada

### Variables de Entorno

```bash
cp .env.example .env
```

Editar `.env` con:

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `GOOGLE_API_KEY` | API key de Google Gemini | ✅ |
| `DATABASE_URL` | Connection string PostgreSQL | Default en compose |
| `API_KEYS_CONFIG` | JSON con API keys y scopes | Para auth |

### Levantar Servicios

```bash
# Instalar dependencias
pnpm install

# Levantar PostgreSQL (db) + Backend (rag-api)
pnpm docker:up

# Esperar ~30s y verificar
docker compose ps
```

### Generar Contratos

```bash
pnpm contracts:export
pnpm contracts:gen
```

### Ejecutar en Desarrollo

```bash
pnpm dev
```

### Verificar Funcionamiento

```bash
# Health check
curl http://localhost:8000/healthz
# Esperado: {"ok":true,"db":"connected","request_id":"..."}

# Métricas
curl http://localhost:8000/metrics | head -5

# Ingestar documento
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","text":"RAG Corp es un sistema de búsqueda semántica."}'

# Consulta RAG
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Qué es RAG Corp?","top_k":3}'
```

### URLs de Acceso

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Métricas | http://localhost:8000/metrics |

---

## Scripts Útiles

| Script | Descripción |
|--------|-------------|
| `pnpm install` | Instalar dependencias del monorepo |
| `pnpm dev` | Levantar frontend + backend en modo desarrollo |
| `pnpm docker:up` | Iniciar PostgreSQL (db) + Backend (rag-api) |
| `pnpm docker:down` | Detener contenedores y eliminar volúmenes |
| `pnpm contracts:export` | Exportar OpenAPI desde FastAPI |
| `pnpm contracts:gen` | Generar cliente TypeScript con Orval |
| `pnpm build` | Build de producción |
| `pnpm lint` | Lint del monorepo |

### Backend (Python)

```bash
cd backend
pytest -m unit              # Tests unitarios (rápidos)
pytest -m integration       # Tests de integración (requiere DB)
pytest --cov=app            # Con cobertura
```

---

## Estructura del Repo

```
rag-corp/
├── backend/                 # FastAPI + lógica RAG
│   ├── app/
│   │   ├── domain/          # Entidades y Protocols
│   │   ├── application/     # Use cases
│   │   ├── infrastructure/  # Adapters (DB, APIs, chunking)
│   │   ├── main.py          # Entry point FastAPI
│   │   └── routes.py        # Controllers HTTP
│   └── tests/               # Unit + Integration tests
├── frontend/                # Next.js UI
│   ├── app/                 # App Router
│   └── __tests__/           # Tests frontend
├── shared/
│   └── contracts/           # OpenAPI + cliente TS generado
├── infra/
│   └── postgres/            # init.sql (schema + pgvector)
├── doc/                     # Documentación técnica
├── compose.yaml             # Docker Compose desarrollo
├── compose.prod.yaml        # Docker Compose producción
└── .env.example             # Template de variables
```

---

## Documentación

La documentación técnica vive en [`doc/`](doc/README.md):

| Documento | Descripción |
|-----------|-------------|
| [Arquitectura](doc/architecture/overview.md) | Capas, flujos, componentes |
| [API HTTP](doc/api/http-api.md) | Endpoints, auth, errores |
| [Schema DB](doc/data/postgres-schema.md) | PostgreSQL + pgvector |
| [Runbook Local](doc/runbook/local-dev.md) | Desarrollo y troubleshooting |
| [Tests](backend/tests/README.md) | Estructura y ejecución |

---

## Contribución y Calidad

### Tests

```bash
# Backend - unitarios
cd backend && pytest -m unit -v

# Backend - con cobertura
pytest --cov=app --cov-report=html

# Frontend
cd frontend && pnpm test
```

### Convenciones

- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **PRs**: Pequeños, una feature/fix por PR
- **Python**: PEP 8, type hints, docstrings CRC
- **TypeScript**: ESLint + Prettier

### Workflow

1. Fork y crear branch (`git checkout -b feat/mi-feature`)
2. Desarrollar con tests
3. Commit con mensaje descriptivo
4. Push y abrir PR
5. Actualizar docs si el cambio lo requiere

---

## Roadmap

### ✅ Implementado

- [x] Clean Architecture con capas bien definidas
- [x] Autenticación por API Key con scopes
- [x] Rate limiting configurable
- [x] Métricas Prometheus y logging estructurado
- [x] Connection pooling y atomic ingest
- [x] Prompts versionados y externalizados

### 🚧 Pendiente

- [ ] **Streaming**: Respuestas SSE en tiempo real
- [ ] **Multi-turn Chat**: Historial de conversación
- [ ] **Caché de embeddings**: Reducir latencia y costos
- [ ] **Retry logic**: Resiliencia para servicios externos
- [ ] **CI/CD**: GitHub Actions pipeline
- [ ] **Admin UI**: CRUD visual de documentos

---

## Licencia

MIT License - ver [LICENSE](LICENSE)

---

## Links

- 📖 [Documentación Completa](doc/README.md)
- 🐛 [Issues](https://github.com/SaintWyss/rag-corp/issues)
- 📊 [Swagger UI](http://localhost:8000/docs) (local)
