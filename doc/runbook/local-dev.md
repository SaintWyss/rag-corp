# Local Development Runbook

**Project:** RAG Corp  
**Last Updated:** 2026-01-03

---

## Quickstart

```bash
# 1) Configure environment
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY

# 2) Install dependencies
pnpm install

# 3) Start services (db + api)
pnpm docker:up

# 4) Export contracts (OpenAPI -> TS)
pnpm contracts:export
pnpm contracts:gen

# 5) Start dev servers
pnpm dev
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Comandos Útiles (Cheat Sheet)

### Docker Compose

```bash
# Solo base de datos (sin API)
docker compose up -d db

# Ver logs del backend en tiempo real
docker compose logs -f rag-api

# Reset completo (borra datos de DB)
docker compose down -v && docker compose up -d

# Ver estado de servicios
docker compose ps

# Reconstruir imágenes (después de cambios en Dockerfile)
docker compose up -d --build
```

### Testing

```bash
# Tests unitarios (rápidos, sin Docker)
cd backend && pytest -m unit

# Tests de integración (requiere DB corriendo)
cd backend && RUN_INTEGRATION=1 GOOGLE_API_KEY=tu_clave pytest -m integration

# Tests con cobertura HTML
cd backend && pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Base de Datos

```bash
# Conectar a PostgreSQL vía psql
docker compose exec db psql -U postgres -d rag

# Ver tablas
\dt

# Ver chunks almacenados
SELECT id, document_id, chunk_index, LEFT(content, 50) FROM chunks LIMIT 10;
```

### Contratos API

```bash
# Regenerar cliente TypeScript desde OpenAPI
pnpm contracts:export   # FastAPI → openapi.json
pnpm contracts:gen      # openapi.json → generated.ts
```

---

## Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Export OpenAPI locally (sin Docker):

```bash
cd backend
python3 scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

---

## Frontend (Next.js)

```bash
cd frontend
pnpm dev
```

---

## Environment Variables

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `GOOGLE_API_KEY` | ✅ | API Key de Google Gemini |
| `DATABASE_URL` | ✅ | Connection string PostgreSQL |
| `ALLOWED_ORIGINS` | ❌ | CORS origins (default: localhost:3000) |

Ver [`.env.example`](../../.env.example) para valores de ejemplo.

---

## Troubleshooting

### "Connection refused" al correr tests de integración
```bash
# Verificar que PostgreSQL esté corriendo
docker compose ps
docker compose up -d db
```

### "GOOGLE_API_KEY not set"
```bash
# Verificar que .env existe y tiene la variable
cat .env | grep GOOGLE_API_KEY
```

### Frontend no conecta con API
```bash
# Verificar que el proxy en next.config.ts apunta a localhost:8000
# Verificar que el backend está corriendo
curl http://localhost:8000/healthz
```
