# Local Development Runbook

**Project:** RAG Corp  
**Last Updated:** 2025-12-30

This runbook covers common development tasks, troubleshooting, and operational procedures for local development.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Commands](#development-commands)
3. [Database Operations](#database-operations)
4. [Troubleshooting](#troubleshooting)
5. [Testing](#testing)
6. [Code Quality](#code-quality)
7. [Environment Management](#environment-management)
8. [Performance Profiling](#performance-profiling)

---

## Quick Start

### Prerequisites

Ensure you have:
- **Docker + Docker Compose:** For PostgreSQL
- **Python 3.11+:** For backend
- **Node.js 18+:** For frontend
- **pnpm:** Package manager (`npm install -g pnpm`)
- **Google Gemini API Key:** [Get one here](https://makersuite.google.com/app/apikey)

### First-Time Setup

```bash
# 1. Clone repository
git clone https://github.com/SaintWyss/rag-corp.git
cd rag-corp

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 3. Start PostgreSQL
docker compose up -d db

# 4. Install backend dependencies
cd services/rag-api
pip install -r requirements.txt

# 5. Install frontend dependencies
cd ../../apps/web
pnpm install

# 6. Start backend (terminal 1)
cd ../../services/rag-api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. Start frontend (terminal 2)
cd ../../apps/web
pnpm dev

# 8. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Development Commands

### Backend (FastAPI)

```bash
cd services/rag-api

# Start development server (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start with custom log level
uvicorn app.main:app --reload --log-level debug

# Run in background
uvicorn app.main:app --reload &

# Export OpenAPI spec
python scripts/export_openapi.py
# Output: packages/contracts/openapi.json

# Format code
black app/
ruff check app/ --fix

# Type checking
mypy app/

# Check imports
isort app/ --check-only
```

### Frontend (Next.js)

```bash
cd apps/web

# Start development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Lint code
pnpm lint

# Format code
pnpm format

# Type check
pnpm type-check
```

### Monorepo (Turborepo)

```bash
# From project root

# Build all packages
pnpm build

# Run all tests
pnpm test

# Lint all packages
pnpm lint

# Clean all build artifacts
pnpm clean

# Install dependencies for all packages
pnpm install
```

---

## Database Operations

### Start/Stop PostgreSQL

```bash
# Start PostgreSQL
docker compose up -d db

# Stop PostgreSQL
docker compose stop db

# Remove PostgreSQL (deletes data!)
docker compose down -v db

# View logs
docker compose logs -f db

# Check status
docker compose ps
```

### Connect to Database

```bash
# Using psql (from host)
psql -h localhost -U postgres -d rag
# Password: postgres

# Using psql (from Docker)
docker compose exec db psql -U postgres -d rag

# Using pgAdmin (GUI)
# Download from: https://www.pgadmin.org/
# Connection: localhost:5432, user: postgres, password: postgres
```

### Database Queries

```sql
-- Check pgvector extension
\dx

-- List tables
\dt

-- View chunks table schema
\d chunks

-- Count chunks
SELECT COUNT(*) FROM chunks;

-- Count chunks by document
SELECT doc_id, COUNT(*) AS num_chunks
FROM chunks
GROUP BY doc_id
ORDER BY num_chunks DESC;

-- View recent chunks
SELECT id, doc_id, chunk_index, LEFT(content, 50) AS preview
FROM chunks
ORDER BY created_at DESC
LIMIT 10;

-- Check index status
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename = 'chunks';

-- Similarity search (test query)
SELECT
    id,
    doc_id,
    chunk_index,
    LEFT(content, 50) AS preview,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Reset Database

```bash
# Drop and recreate database
docker compose exec db psql -U postgres -c "DROP DATABASE rag;"
docker compose exec db psql -U postgres -c "CREATE DATABASE rag;"

# Re-run init script
docker compose exec db psql -U postgres -d rag -f /docker-entrypoint-initdb.d/00-init.sql

# OR: Restart container (runs init.sql automatically)
docker compose down db
docker compose up -d db
```

### Backup and Restore

```bash
# Backup database
docker compose exec db pg_dump -U postgres rag > backup_$(date +%Y%m%d).sql

# Restore database
docker compose exec -T db psql -U postgres -d rag < backup_20251230.sql

# Backup with compression
docker compose exec db pg_dump -U postgres rag | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore compressed backup
gunzip -c backup_20251230.sql.gz | docker compose exec -T db psql -U postgres -d rag
```

---

## Troubleshooting

### Backend Issues

#### "ModuleNotFoundError: No module named 'app'"

**Problem:** Python can't find the app module.

**Solution:**
```bash
# Ensure you're in the correct directory
cd services/rag-api

# Set PYTHONPATH (if needed)
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Or run with python -m
python -m uvicorn app.main:app --reload
```

#### "Connection refused: PostgreSQL"

**Problem:** Backend can't connect to database.

**Solution:**
```bash
# Check if PostgreSQL is running
docker compose ps db

# Start PostgreSQL if not running
docker compose up -d db

# Check connection string in .env
# Should be: DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag

# Test connection manually
psql -h localhost -U postgres -d rag
```

#### "google.generativeai.types.generation_types.StopCandidateException"

**Problem:** Gemini API blocked the request (safety filters).

**Solution:**
```python
# Adjust safety settings in google_llm_service.py
response = self.model.generate_content(
    prompt,
    safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    }
)
```

#### "429 Too Many Requests: Gemini API"

**Problem:** Rate limit exceeded.

**Solution:**
- Wait 60 seconds and retry
- Upgrade to paid Gemini API tier
- Implement request throttling

```python
# Add retry logic with exponential backoff
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
def embed_with_retry(text):
    return genai.embed_content(...)
```

### Frontend Issues

#### "Port 3000 already in use"

**Problem:** Another process is using port 3000.

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
PORT=3001 pnpm dev
```

#### "Failed to fetch: http://localhost:8000/ask"

**Problem:** Frontend can't reach backend.

**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/healthz

# Check CORS configuration in backend (main.py)
# Ensure http://localhost:3000 is allowed

# Check environment variables in Next.js
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Database Issues

#### "pgvector extension not found"

**Problem:** pgvector extension not installed.

**Solution:**
```bash
# Use pgvector image (not plain postgres)
# In docker-compose.yml:
services:
  postgres:
    image: pgvector/pgvector:pg16  # ✅ Correct
    # NOT: postgres:16             # ❌ Wrong
```

#### "Index scan not being used"

**Problem:** Query is slow (sequential scan instead of index).

**Solution:**
```sql
-- Check if index exists
\d chunks

-- Recreate IVFFlat index
DROP INDEX IF EXISTS chunks_embedding_idx;
CREATE INDEX chunks_embedding_idx
ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Update statistics
ANALYZE chunks;

-- Set probes for queries
SET ivfflat.probes = 20;
```

---

## Testing

### Run Tests

```bash
# Backend unit tests
cd services/rag-api
pytest tests/unit/ -v

# Backend integration tests (requires database)
pytest tests/integration/ -v

# Run specific test
pytest tests/unit/test_answer_query_use_case.py::test_answer_query_with_results -v

# Run with coverage
pytest --cov=app --cov-report=html

# Frontend tests
cd apps/web
pnpm test

# E2E tests
pytest tests/e2e/ -v --headed
```

### Test Database

```bash
# Start test database (different port)
docker-compose -f docker-compose.test.yml up -d

# Run integration tests with test DB
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/rag_test_db \
pytest tests/integration/

# Stop test database
docker-compose -f docker-compose.test.yml down -v
```

---

## Code Quality

### Linting and Formatting

```bash
# Backend
cd services/rag-api

# Format code
black app/
isort app/

# Lint
ruff check app/ --fix
mypy app/

# Frontend
cd apps/web

# Format
pnpm format

# Lint
pnpm lint

# Type check
pnpm type-check
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

---

## Environment Management

### Environment Variables

**.env.example:**
```bash
# Backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
GOOGLE_API_KEY=your-google-api-key-here

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=development

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Load Environment Variables

```bash
# Backend (Python)
# Uses python-dotenv (loads .env automatically)
from dotenv import load_dotenv
load_dotenv()

# Frontend (Next.js)
# Prefix with NEXT_PUBLIC_ for browser access
# Automatically loaded by Next.js

# Manual export
export GOOGLE_API_KEY=your-key
export DATABASE_URL=postgresql://...
```

---

## Performance Profiling

### Backend Profiling

```python
# Profile endpoint with cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Execute code
result = use_case.execute(input)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Database Query Performance

```sql
-- Explain query plan
EXPLAIN ANALYZE
SELECT *
FROM chunks
ORDER BY embedding <=> '[0.1, ...]'::vector
LIMIT 5;

-- Check slow queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### API Response Time

```bash
# Time a single request
time curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG Corp?"}'

# Benchmark with wrk (install: brew install wrk)
wrk -t4 -c100 -d30s --latency \
  -s post.lua \
  http://localhost:8000/ask
```

**post.lua:**
```lua
wrk.method = "POST"
wrk.body   = '{"query": "test"}'
wrk.headers["Content-Type"] = "application/json"
```

---

## Useful Scripts

### Ingest Test Document

```bash
# Ingest sample document
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "test-doc",
    "text": "RAG Corp is a retrieval-augmented generation system for corporate documents. It uses Google Gemini for embeddings and text generation. Documents are chunked into 900-character segments with 120-character overlap."
  }'
```

### Query Documents

```bash
# Semantic search
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does chunking work?", "limit": 3}'

# RAG Q&A
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What LLM does RAG Corp use?"}'
```

### Monitor Logs

```bash
# Backend logs
cd services/rag-api
uvicorn app.main:app --reload --log-level debug

# PostgreSQL logs
docker-compose logs -f postgres

# Tail all logs
docker-compose logs -f
```

---

## Common Tasks Checklist

### Starting Development

- [ ] Pull latest changes: `git pull`
- [ ] Start PostgreSQL: `docker-compose up -d postgres`
- [ ] Start backend: `cd services/rag-api && uvicorn app.main:app --reload`
- [ ] Start frontend: `cd apps/web && pnpm dev`
- [ ] Verify API: `curl http://localhost:8000/healthz`

### Before Committing

- [ ] Format code: `black app/ && isort app/`
- [ ] Run linter: `ruff check app/`
- [ ] Run tests: `pytest tests/unit/ -v`
- [ ] Check types: `mypy app/`
- [ ] Update docs if needed

### Deploying Changes

- [ ] Run all tests: `pytest tests/`
- [ ] Build production: `pnpm build`
- [ ] Check Docker build: `docker-compose build`
- [ ] Update CHANGELOG.md
- [ ] Create pull request

---

## References

- **Docker Compose:** [compose.yaml](../../compose.yaml)
- **API Documentation:** [http-api.md](../api/http-api.md)
- **Testing Guide:** [testing.md](../quality/testing.md)
- **Architecture:** [overview.md](../architecture/overview.md)

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
