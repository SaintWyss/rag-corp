# Local Development Runbook

**Project:** RAG Corp  
**Last Updated:** 2026-01-02

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

## Backend (FastAPI)

```bash
cd services/rag-api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Export OpenAPI locally:

```bash
cd services/rag-api
python3 scripts/export_openapi.py --out ../../packages/contracts/openapi.json
```

---

## Frontend (Next.js)

```bash
cd apps/web
pnpm dev
```

---

## Database

```bash
# Start only DB
docker compose up -d db

# Stop DB
docker compose stop db

# Reset DB (data loss)
docker compose down -v

# Connect via psql
docker compose exec db psql -U postgres -d rag
```

---

## Environment Variables

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
GOOGLE_API_KEY=your-google-api-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Testing

```bash
# Unit tests (offline)
cd services/rag-api
pytest -m unit

# Integration tests (requires DB + GOOGLE_API_KEY)
RUN_INTEGRATION=1 GOOGLE_API_KEY=your-key pytest -m integration

# All tests (integration skipped unless RUN_INTEGRATION=1)
pytest
```
