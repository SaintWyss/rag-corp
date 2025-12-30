"""
Name: PostgreSQL Document Repository Implementation

Responsibilities:
  - Implement DocumentRepository interface for PostgreSQL + pgvector
  - Manage database connections with vector support
  - Perform vector similarity searches using cosine distance
  - Map between domain entities and database rows

Collaborators:
  - domain.repositories.DocumentRepository: Interface implementation
  - domain.entities: Document, Chunk
  - psycopg: PostgreSQL driver
  - pgvector: Vector extension

Constraints:
  - Non-pooled connections (creates new connection per operation)
  - Fixed 768-dimensional embeddings
  - No retry logic for transient failures

Notes:
  - Implements Repository pattern from domain layer
  - Uses dependency inversion (domain doesn't depend on this)
  - Can be swapped with other implementations (e.g., Pinecone)
"""

import os
from uuid import UUID, uuid4
from typing import List
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Json

from ...domain.entities import Document, Chunk
from ...domain.repositories import DocumentRepository


# R: Database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag")


class PostgresDocumentRepository:
    """
    R: PostgreSQL implementation of DocumentRepository.
    
    Implements domain.repositories.DocumentRepository interface
    using PostgreSQL with pgvector extension.
    """
    
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
    
    def save_document(self, document: Document) -> None:
        """
        R: Persist document metadata to PostgreSQL.
        
        Implements DocumentRepository.save_document()
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
                (document.id, document.title, document.source, Json(document.metadata)),
            )
    
    def save_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None:
        """
        R: Persist chunks with embeddings to PostgreSQL.
        
        Implements DocumentRepository.save_chunks()
        """
        with self._conn() as conn:
            # R: Insert each chunk with its embedding
            for chunk in chunks:
                # R: Generate unique chunk ID if not provided
                cid = chunk.chunk_id or uuid4()
                
                # R: Store chunk with embedding vector
                conn.execute(
                    """
                    INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cid, document_id, chunk.chunk_index or 0, chunk.content, chunk.embedding),
                )
    
    def find_similar_chunks(
        self, 
        embedding: List[float], 
        top_k: int
    ) -> List[Chunk]:
        """
        R: Search for similar chunks using vector cosine similarity.
        
        Implements DocumentRepository.find_similar_chunks()
        
        Returns:
            List of Chunk entities ordered by similarity (descending)
        """
        with self._conn() as conn:
            # R: Execute vector similarity search using cosine distance
            rows = conn.execute(
                """
                SELECT
                  id,
                  document_id,
                  chunk_index,
                  content,
                  embedding,
                  (1 - (embedding <=> %s::vector)) as score
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, top_k),
            ).fetchall()
        
        # R: Convert database rows to Chunk entities
        return [
            Chunk(
                chunk_id=r[0],
                document_id=r[1],
                chunk_index=r[2],
                content=r[3],
                embedding=r[4],
            )
            for r in rows
        ]
