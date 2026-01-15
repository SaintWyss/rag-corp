# PostgreSQL Database Schema

**Project:** RAG Corp  
**Database:** PostgreSQL 16  
**Extension:** pgvector 0.8.1  
**Last Updated:** 2026-01-15

---

## Table of Contents

1. [Overview](#overview)
2. [Schema](#schema)
3. [Indexes](#indexes)
4. [Vector Operations](#vector-operations)
5. [Query Examples](#query-examples)
6. [Performance Tuning](#performance-tuning)
7. [Backup and Maintenance](#backup-and-maintenance)
8. [Connection Pooling](#connection-pooling)
9. [Statement Timeout](#statement-timeout)
10. [pgvector Index Reindexing](#pgvector-index-reindexing)

---

## Overview

RAG Corp uses PostgreSQL with the `pgvector` extension to store document chunks and their vector embeddings. The schema is optimized for:

- **Vector similarity search** (cosine distance)
- **Metadata filtering** (by document ID, user, etc.)
- **Hybrid queries** (vector + relational filters)

### Key Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `documents` | Document metadata + upload status | 1K-1M |
| `chunks` | Document chunks with embeddings | 10K-1M |
| `users` | JWT users (admin/employee) | 10-10K |
| `audit_events` | Audit trail | 1K-1M |

---

## Schema

### Extension: pgvector

```sql
-- Enable vector extension (required for embedding storage)
CREATE EXTENSION IF NOT EXISTS vector;
```

**Purpose:** Adds support for:
- `vector` data type (for embeddings)
- Vector distance operators (`<=>`, `<->`, `<#>`)
- Vector indexes (IVFFlat, HNSW)

### Table: documents

Stores document metadata only.

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    file_name TEXT,
    mime_type TEXT,
    storage_key TEXT,
    uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT,
    error_message TEXT,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
    allowed_roles TEXT[]
);

ALTER TABLE documents ADD CONSTRAINT ck_documents_status
CHECK (status IS NULL OR status IN ('PENDING', 'PROCESSING', 'READY', 'FAILED'));
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Document identifier |
| `title` | TEXT | NO | Document title |
| `source` | TEXT | YES | Optional source URL/identifier |
| `metadata` | JSONB | NO | Custom metadata |
| `created_at` | TIMESTAMPTZ | NO | Creation timestamp |
| `deleted_at` | TIMESTAMPTZ | YES | Soft delete timestamp |
| `file_name` | TEXT | YES | Nombre de archivo subido |
| `mime_type` | TEXT | YES | MIME del archivo |
| `storage_key` | TEXT | YES | Key en S3/MinIO |
| `uploaded_by_user_id` | UUID | YES | Usuario que subio el archivo |
| `status` | TEXT | YES | PENDING/PROCESSING/READY/FAILED |
| `error_message` | TEXT | YES | Error de procesamiento |
| `tags` | TEXT[] | NO | Tags normalizados |
| `allowed_roles` | TEXT[] | YES | ACL por rol (admin/employee) |

### Table: users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users ADD CONSTRAINT ck_users_role
CHECK (role IN ('admin', 'employee'));
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | User identifier |
| `email` | TEXT | NO | Unique email |
| `password_hash` | TEXT | NO | Argon2 hash |
| `role` | TEXT | NO | admin/employee |
| `is_active` | BOOLEAN | NO | Soft disable |
| `created_at` | TIMESTAMPTZ | NO | Creation timestamp |

### Table: audit_events

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Audit event ID |
| `actor` | TEXT | NO | `user:<id>` o `service:<hash>` |
| `action` | TEXT | NO | Evento (`documents.upload`, `auth.login`, etc.) |
| `target_id` | UUID | YES | Entidad afectada |
| `metadata` | JSONB | NO | Metadata asociada |
| `created_at` | TIMESTAMPTZ | NO | Timestamp |

### Table: chunks

Stores text chunks with their vector embeddings.

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Chunk identifier |
| `document_id` | UUID | NO | Parent document |
| `chunk_index` | INTEGER | NO | Chunk position in document (0-based) |
| `content` | TEXT | NO | Chunk text content (typically 900 chars) |
| `embedding` | vector(768) | NO | 768-dimensional embedding vector |
| `metadata` | JSONB | NO | Chunk metadata |
| `created_at` | TIMESTAMPTZ | NO | Insertion timestamp |

**Design Decisions:**

- **768 dimensions:** Matches Gemini text-embedding-004 output
- **UUID IDs:** Consistent with API models
- **Cascade delete:** Deleting a document removes its chunks

---

## Indexes

Note: Alembic creates `chunks_embedding_idx`. Primary keys and `users.email` unique index are implicit, and the optional indexes below are not created by default.

### Primary Key Indexes (Implicit)

```sql
-- Automatically created by PRIMARY KEY constraints; no manual DDL needed
```

**Purpose:** Fast lookup by ID  
**Type:** B-tree  
**Usage:** `SELECT * FROM documents WHERE id = '...'`

### Vector Similarity Index (IVFFlat)

```sql
-- Create IVFFlat index for approximate nearest neighbor search
CREATE INDEX chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Parameters:**
- **Type:** IVFFlat (Inverted File with Flat compression)
- **Operator:** `vector_cosine_ops` (cosine distance)
- **Lists:** 100 (number of clusters)

**Tuning Guidelines:**
- **Lists:** `sqrt(num_rows)` is a good starting point
- For 10K rows: `lists = 100` (√10,000)
- For 100K rows: `lists = 300` (√100,000)
- For 1M rows: `lists = 1000` (√1,000,000)

**Trade-offs:**
- More lists → Better recall, slower index build
- Fewer lists → Faster queries, lower recall

### Document ID Index (Optional)

```sql
-- For filtering by document ID
CREATE INDEX chunks_document_id_idx ON chunks (document_id);
```

**Purpose:** Fast lookup by document (not created by default)  
**Usage:** `SELECT * FROM chunks WHERE document_id = '...'`

### Composite Index (Optional)

```sql
-- For pagination within a document
CREATE INDEX chunks_document_chunk_idx ON chunks (document_id, chunk_index);
```

**Purpose:** Retrieve all chunks for a document in order (not created by default)  
**Usage:** `SELECT * FROM chunks WHERE document_id = '...' ORDER BY chunk_index`

---

## Vector Operations

### Distance Operators

pgvector provides three distance operators:

| Operator | Distance Metric | Formula | Use Case |
|----------|-----------------|---------|----------|
| `<=>` | **Cosine distance** | `1 - cos(θ)` | Text similarity (preferred) |
| `<->` | Euclidean (L2) | `√Σ(a - b)²` | Geometric distance |
| `<#>` | Inner product | `-Σ(a × b)` | Normalized vectors |

**Recommendation:** Use `<=>` (cosine distance) for text embeddings.

### Similarity Conversion

Cosine distance returns `0-2` (0 = identical, 2 = opposite).  
Convert to similarity score (0-1):

```sql
SELECT 
    id,
    content,
    1 - (embedding <=> query_embedding) AS similarity
FROM chunks
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

**Similarity Interpretation:**
- `> 0.9`: Highly similar
- `0.7-0.9`: Relevant
- `0.5-0.7`: Somewhat related
- `< 0.5`: Unrelated

---

## Query Examples

### 1. Insert Document + Chunk

```sql
INSERT INTO documents (id, title, source, metadata)
VALUES (
    '3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d',
    'User Guide 2024',
    'https://example.com/docs/user-guide',
    '{}'::jsonb
);
```

```sql
INSERT INTO chunks (document_id, chunk_index, content, embedding)
VALUES (
    '3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d',
    0,
    'RAG Corp is a retrieval-augmented generation system...',
    '[0.123, -0.456, 0.789, ...]'::vector  -- 768 values
);
```

### 2. Vector Similarity Search

Find top-5 most similar chunks to a query embedding:

```sql
SELECT 
    id,
    document_id,
    chunk_index,
    content,
    1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) AS similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;
```

**Performance:** ~10ms for 50K chunks (with IVFFlat index)

### 3. Hybrid Query (Vector + Metadata Filter)

Search within a specific document:

```sql
SELECT 
    id,
    chunk_index,
    content,
    1 - (embedding <=> $1::vector) AS similarity
FROM chunks
WHERE document_id = '3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d'
  AND embedding IS NOT NULL
ORDER BY embedding <=> $1::vector  -- Vector similarity
LIMIT 5;
```

### 4. Retrieve All Chunks for a Document

```sql
SELECT chunk_index, content
FROM chunks
WHERE document_id = '3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d'
ORDER BY chunk_index;
```

### 5. Count Chunks per Document

```sql
SELECT document_id, COUNT(*) AS num_chunks
FROM chunks
GROUP BY document_id
ORDER BY num_chunks DESC;
```

### 6. Delete Document

```sql
DELETE FROM documents
WHERE id = '3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d';
```

### 7. Exact Nearest Neighbor (No Index)

For debugging or benchmarking:

```sql
SET enable_indexscan = OFF;  -- Disable index, force sequential scan

SELECT 
    id,
    content,
    1 - (embedding <=> $1::vector) AS similarity
FROM chunks
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

**Note:** Slow for large datasets (scans all rows).

---

## Performance Tuning

### Index Build

**Initial Build:**
```sql
-- Takes 5-10 minutes for 100K rows
CREATE INDEX chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Parallel Workers:**
```sql
SET max_parallel_maintenance_workers = 4;
CREATE INDEX CONCURRENTLY chunks_embedding_idx ...;
```

### Query Performance

**Set probes at query time:**
```sql
-- Default: probes = lists / 10 (e.g., 10 for lists=100)
SET ivfflat.probes = 20;  -- Increase for better recall

SELECT ...
FROM chunks
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

**Trade-offs:**
- More probes → Better recall, slower queries
- Fewer probes → Faster queries, lower recall

**Recommended:**
- Development: `probes = 20` (better accuracy)
- Production: `probes = 10` (faster queries)

### Query Plan Analysis

```sql
EXPLAIN ANALYZE
SELECT ...
FROM chunks
ORDER BY embedding <=> '[...]'::vector
LIMIT 5;
```

**Look for:**
- `Index Scan using chunks_embedding_idx` ✅ (good)
- `Seq Scan on chunks` ❌ (bad: no index used)

### Statistics Update

```sql
ANALYZE chunks;
```

Run after bulk inserts to update query planner statistics.

---

## Backup and Maintenance

### Backup Database

```bash
# Full backup (includes pgvector extension)
pg_dump -h localhost -U postgres rag > backup.sql

# Compressed backup
pg_dump -h localhost -U postgres rag | gzip > backup.sql.gz
```

### Restore Database

```bash
# Restore from backup
psql -h localhost -U postgres -d rag < backup.sql

# Restore compressed
gunzip -c backup.sql.gz | psql -h localhost -U postgres -d rag
```

### Vacuum and Analyze

```sql
-- Reclaim storage and update statistics
VACUUM ANALYZE chunks;
```

Run weekly or after large deletions.

### Index Rebuild

```sql
-- Rebuild index (if corrupted or after bulk updates)
DROP INDEX chunks_embedding_idx;
CREATE INDEX chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Monitor Index Health

```sql
-- Check index size
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE tablename = 'chunks';

-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('chunks')) AS total_size;
```

---

## Schema Migrations

### Add New Column

```sql
ALTER TABLE chunks
ADD COLUMN user_id VARCHAR(100);

CREATE INDEX chunks_user_id_idx ON chunks (user_id);
```

### Change Vector Dimension (Requires Recreation)

```sql
-- Drop old index
DROP INDEX chunks_embedding_idx;

-- Alter column (drops data!)
ALTER TABLE chunks
ALTER COLUMN embedding TYPE vector(1024);

-- Recreate index
CREATE INDEX chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Warning:** Changing vector dimension requires re-embedding all documents.

---

## Connection Strings

### Local Development

```bash
# Environment variable
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rag"

# psycopg (Python)
import psycopg
conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/rag")
```

### Docker Compose

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: rag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
```

---

## Connection Pooling

RAG Corp uses `psycopg_pool` for connection pooling. This reduces connection overhead and improves performance under load.

### Configuration

Pool settings are controlled via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_MIN_SIZE` | 2 | Minimum idle connections |
| `DB_POOL_MAX_SIZE` | 10 | Maximum connections |
| `DB_STATEMENT_TIMEOUT_MS` | 30000 | Query timeout (ms) |

### Pool Initialization

The pool is initialized in `app/main.py` lifespan:

```python
from app.infrastructure.db.pool import init_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool(
        db_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size
    )
    yield
    close_pool()
```

### Pool Usage in Repository

```python
from app.infrastructure.db.pool import get_pool

pool = get_pool()
with pool.connection() as conn:
    result = conn.execute("SELECT ...")
```

### Sizing Guidelines

| Workload | Min Size | Max Size | Notes |
|----------|----------|----------|-------|
| Development | 2 | 10 | Default settings |
| Light production | 5 | 20 | Small instance |
| Heavy production | 10 | 50 | High concurrency |

**Formula:** `max_size = num_workers * 2` (for sync workers)

### Troubleshooting

**Pool exhaustion:**
```
psycopg_pool.PoolTimeout: getconn timeout
```
- Increase `DB_POOL_MAX_SIZE`
- Check for connection leaks (unclosed connections)

**Connection refused:**
```
psycopg.OperationalError: could not connect
```
- Verify PostgreSQL is running
- Check `DATABASE_URL` is correct

---

## Statement Timeout

Protects against long-running queries that could block resources.

### Configuration

Set via environment variable:

```bash
# 30 seconds (default)
export DB_STATEMENT_TIMEOUT_MS=30000

# Disable timeout (not recommended for production)
export DB_STATEMENT_TIMEOUT_MS=0
```

### How It Works

Timeout is set per session via pool configure callback:

```python
def _configure_connection(conn):
    register_vector(conn)
    if timeout_ms > 0:
        conn.execute(f"SET statement_timeout = {timeout_ms}")
```

### Error Handling

When timeout is exceeded:

```
psycopg.errors.QueryCanceled: canceling statement due to statement timeout
```

Handle in application code:

```python
from psycopg.errors import QueryCanceled

try:
    result = conn.execute(slow_query)
except QueryCanceled:
    logger.warning("Query cancelled due to timeout")
    raise HTTPException(504, "Query timeout")
```

---

## pgvector Index Reindexing

When to rebuild the IVFFlat index:

### Signs You Need Reindexing

1. **Query performance degraded** after many inserts/deletes
2. **Recall dropped** (relevant results not appearing)
3. **Index bloat** (index size > 2x expected)

### Reindex Procedure

```sql
-- 1. Check current index status
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE tablename = 'chunks';

-- 2. Drop old index
DROP INDEX chunks_embedding_idx;

-- 3. Calculate optimal lists based on row count
SELECT COUNT(*) AS row_count, 
       SQRT(COUNT(*))::int AS recommended_lists 
FROM chunks;

-- 4. Rebuild with optimal settings
CREATE INDEX chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Adjust based on row count

-- 5. Update statistics
ANALYZE chunks;
```

### Concurrent Reindexing (Production)

```sql
-- Avoid locking the table
CREATE INDEX CONCURRENTLY chunks_embedding_idx_new
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Swap indexes
DROP INDEX chunks_embedding_idx;
ALTER INDEX chunks_embedding_idx_new RENAME TO chunks_embedding_idx;
```

### Scheduling

| Data Growth | Reindex Frequency |
|-------------|-------------------|
| < 10% monthly | Quarterly |
| 10-50% monthly | Monthly |
| > 50% monthly | Weekly |

---

## References

- **pgvector GitHub:** https://github.com/pgvector/pgvector
- **pgvector Performance Guide:** https://github.com/pgvector/pgvector#performance
- **PostgreSQL Docs:** https://www.postgresql.org/docs/16/
- **Alembic Migration:** [backend/alembic/versions/001_initial.py](../../backend/alembic/versions/001_initial.py)
- **Init SQL (pgvector extension):** [infra/postgres/init.sql](../../infra/postgres/init.sql)

---

**Last Updated:** 2026-01-13  
**Maintainer:** Engineering Team
