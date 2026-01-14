/*
 * Name: PostgreSQL Schema with pgvector Extension
 * 
 * Responsibilities:
 *   - Create pgvector extension for vector operations
 *   - Define documents (metadata) and chunks (content + embeddings) tables
 *   - Establish relationships (FK with CASCADE delete)
 *   - Create IVFFlat index for efficient similarity searches
 * 
 * Collaborators:
 *   - pgvector extension (tested with 0.8.1)
 *   - PostgreSQL 16 (pgvector image uses PG16)
 * 
 * Constraints:
 *   - Fixed 768-dimensional embeddings (Google embedding-004)
 *   - IVFFlat index with lists=100 (adjust based on volume)
 *   - No partitioning (scales up to ~1M chunks)
 * 
 * Notes:
 *   - IF NOT EXISTS allows re-running script without errors
 *   - TIMESTAMPTZ uses UTC timezone by default
 *   - JSONB metadata allows flexibility without migrations
 * 
 * Performance:
 *   - IVFFlat appropriate for datasets <10M vectors
 *   - lists=100 balances precision and speed
 *   - Consider HNSW for datasets >10M (PostgreSQL 15+)
 * 
 * Indexes:
 *   - PK automatic on id (B-tree)
 *   - FK automatic on document_id (B-tree)
 *   - IVFFlat manual on embedding (line 40)
 *   - TODO: Add index on documents.title if used in searches
 */

-- R: Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- R: Documents table (stores metadata only)
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,  -- R: Unique document identifier
  title TEXT NOT NULL,  -- R: Document title
  source TEXT,  -- R: Optional source URL or identifier
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,  -- R: Flexible custom metadata
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- R: Creation timestamp (UTC)
  deleted_at TIMESTAMPTZ  -- R: Soft delete timestamp (NULL if active)
);

-- R: Chunks table (stores content + embeddings)
CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY,  -- R: Unique chunk identifier
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,  -- R: Parent document (cascading delete)
  chunk_index INT NOT NULL,  -- R: Position in document (0-based)
  content TEXT NOT NULL,  -- R: Text fragment
  embedding VECTOR(768) NOT NULL,  -- R: 768-dimensional embedding from text-embedding-004
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,  -- R: Chunk-specific metadata
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()  -- R: Creation timestamp (UTC)
);

-- R: Vector index for efficient cosine similarity searches
-- IVFFlat divides dataset into 100 clusters (adjust based on volume)
CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);  -- R: Number of clusters (tune for dataset size)
