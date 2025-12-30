CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  source TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY,
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(768) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índice para búsquedas vectoriales eficientes
-- ivfflat es apropiado para datasets medianos/grandes
CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
