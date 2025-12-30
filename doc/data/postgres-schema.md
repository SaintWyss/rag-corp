# PostgreSQL Database Schema

**Project:** RAG Corp  
**Database:** PostgreSQL 16  
**Extension:** pgvector 0.8.1  
**Last Updated:** 2025-12-30

---

## Table of Contents

1. [Overview](#overview)
2. [Schema](#schema)
3. [Indexes](#indexes)
4. [Vector Operations](#vector-operations)
5. [Query Examples](#query-examples)
6. [Performance Tuning](#performance-tuning)
7. [Backup and Maintenance](#backup-and-maintenance)

---

## Overview

RAG Corp uses PostgreSQL with the `pgvector` extension to store document chunks and their vector embeddings. The schema is optimized for:

- **Vector similarity search** (cosine distance)
- **Metadata filtering** (by document ID, user, etc.)
- **Hybrid queries** (vector + relational filters)

### Key Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `chunks` | Document chunks with embeddings | 10K-1M |

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

### Table: chunks

Stores text chunks with their vector embeddings.

```sql
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),  -- Gemini text-embedding-004 produces 768D vectors
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Composite unique constraint (one document can have multiple chunks)
    UNIQUE(doc_id, chunk_index)
);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Auto-incrementing primary key |
| `doc_id` | VARCHAR(255) | NO | Document identifier (user-defined) |
| `chunk_index` | INTEGER | NO | Chunk position in document (0-based) |
| `content` | TEXT | NO | Chunk text content (typically 900 chars) |
| `embedding` | vector(768) | YES | 768-dimensional embedding vector |
| `created_at` | TIMESTAMP | NO | Insertion timestamp (default: now) |

**Design Decisions:**

- **768 dimensions:** Matches Gemini text-embedding-004 output
- **UNIQUE(doc_id, chunk_index):** Prevent duplicate chunks
- **TEXT content:** No length limit (supports large chunks)
- **Nullable embedding:** Allows ingestion before embedding generation

---

## Indexes

### Primary Key Index

```sql
-- Automatically created with PRIMARY KEY
CREATE INDEX chunks_pkey ON chunks (id);
```

**Purpose:** Fast lookup by ID  
**Type:** B-tree  
**Usage:** `SELECT * FROM chunks WHERE id = 123`

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
CREATE INDEX chunks_doc_id_idx ON chunks (doc_id);
```

**Purpose:** Fast lookup by document  
**Usage:** `SELECT * FROM chunks WHERE doc_id = 'user-guide-2024'`

### Composite Index (Optional)

```sql
-- For pagination within a document
CREATE INDEX chunks_doc_chunk_idx ON chunks (doc_id, chunk_index);
```

**Purpose:** Retrieve all chunks for a document in order  
**Usage:** `SELECT * FROM chunks WHERE doc_id = 'doc1' ORDER BY chunk_index`

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

### 1. Insert Chunk with Embedding

```sql
INSERT INTO chunks (doc_id, chunk_index, content, embedding)
VALUES (
    'user-guide-2024',
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
    doc_id,
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
WHERE doc_id = 'user-guide-2024'  -- Filter by metadata
  AND embedding IS NOT NULL
ORDER BY embedding <=> $1::vector  -- Vector similarity
LIMIT 5;
```

### 4. Retrieve All Chunks for a Document

```sql
SELECT chunk_index, content
FROM chunks
WHERE doc_id = 'company-policy'
ORDER BY chunk_index;
```

### 5. Count Chunks per Document

```sql
SELECT doc_id, COUNT(*) AS num_chunks
FROM chunks
GROUP BY doc_id
ORDER BY num_chunks DESC;
```

### 6. Delete Document

```sql
DELETE FROM chunks
WHERE doc_id = 'old-document';
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

## References

- **pgvector GitHub:** https://github.com/pgvector/pgvector
- **pgvector Performance Guide:** https://github.com/pgvector/pgvector#performance
- **PostgreSQL Docs:** https://www.postgresql.org/docs/16/
- **Init SQL:** [infra/postgres/init.sql](../../infra/postgres/init.sql)

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
