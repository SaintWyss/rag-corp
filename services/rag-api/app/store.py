"""
Name: PostgreSQL Document Repository

Responsibilities:
  - Manage PostgreSQL connections with pgvector support
  - Persist documents (metadata) and chunks (content + embeddings)
  - Execute vector similarity searches using <=> operator
  - Ensure referential integrity (CASCADE deletes)

Collaborators:
  - psycopg: PostgreSQL driver with autocommit enabled
  - pgvector: Extension for vector operations (cosine similarity)

Constraints:
  - Non-pooled connections (creates new connection per operation)
  - No retry logic for transient failures
  - Fixed 768-dimensional embeddings (Google embedding-004)
  - No index on documents.title (add if searching by title is needed)

Notes:
  - IVFFlat index on chunks.embedding optimizes searches to O(log n)
  - DATABASE_URL must point to PostgreSQL with pgvector extension installed
  - Explicit ::vector cast required in queries (line 50)

Performance:
  - Vector searches with typical top_k (3-10) are sub-second
  - Batch inserts could be optimized with executemany (currently loop)
"""
import os
from uuid import UUID, uuid4
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Json

# R: Database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag")


class Store:
    """Repository pattern for RAG documents with vector storage"""
    
    def _conn(self):
        """
        R: Create PostgreSQL connection with autocommit and vector type registration.
        
        Returns:
            psycopg.Connection: Connection configured for vector operations
        """
        # R: Establish connection with autocommit (no manual transaction management)
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        
        # R: Register pgvector type for embedding operations
        register_vector(conn)
        
        return conn

    def upsert_document(self, document_id: UUID, title: str, source: str | None, metadata: dict):
        """
        R: Insert or update document metadata in PostgreSQL.
        
        Args:
            document_id: Unique document identifier
            title: Document title
            source: Optional source URL or identifier
            metadata: Additional custom metadata (stored as JSONB)
        """
        with self._conn() as conn:
            # R: Upsert document (insert or update if exists)
            conn.execute(
                """
                INSERT INTO documents (id, title, source, metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET title = EXCLUDED.title,
                    source = EXCLUDED.source,
                    metadata = EXCLUDED.metadata
                """,
                (document_id, title, source, Json(metadata)),
            )

    def insert_chunks(self, document_id: UUID, chunks: list[str], vectors: list[list[float]]):
        """
        R: Insert document chunks with their embeddings into PostgreSQL.
        
        Args:
            document_id: Parent document UUID
            chunks: List of text fragments
            vectors: List of 768-dimensional embeddings (parallel to chunks)
        
        Notes:
            - Uses loop with execute (sufficient for MVP)
            - Could be optimized with executemany for bulk inserts
        """
        with self._conn() as conn:
            # R: Insert each chunk with its embedding
            for idx, (content, emb) in enumerate(zip(chunks, vectors)):
                # R: Generate unique chunk ID
                cid = uuid4()
                
                # R: Store chunk with embedding vector
                conn.execute(
                    """
                    INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cid, document_id, idx, content, emb),
                )

    def search(self, query_vec: list[float], top_k: int = 5):
        """
        R: Search for similar chunks using vector cosine similarity.
        
        Args:
            query_vec: Query embedding (768 dimensions)
            top_k: Number of most similar chunks to return
        
        Returns:
            List of dicts with keys: chunk_id, document_id, content, score
            Score is 0-1, higher means more similar (1 - cosine_distance)
        
        Notes:
            - Uses <=> operator for cosine distance (pgvector)
            - Explicit ::vector cast required for query parameter
            - IVFFlat index accelerates search
        """
        with self._conn() as conn:
            # R: Execute vector similarity search using cosine distance
            rows = conn.execute(
                """
                SELECT
                  id as chunk_id,
                  document_id,
                  content,
                  (1 - (embedding <=> %s::vector)) as score
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vec, query_vec, top_k),
            ).fetchall()

        # R: Convert database rows to dictionaries
        return [
            {"chunk_id": r[0], "document_id": r[1], "content": r[2], "score": r[3]}
            for r in rows
        ]
