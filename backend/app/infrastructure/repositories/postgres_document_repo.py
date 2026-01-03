"""
Name: PostgreSQL Document Repository Implementation

Responsibilities:
  - Implement DocumentRepository interface for PostgreSQL + pgvector
  - Use connection pool for efficient connection reuse
  - Atomic operations with transactions
  - Batch insert for performance
  - Vector similarity searches using cosine distance

Collaborators:
  - domain.repositories.DocumentRepository: Interface implementation
  - domain.entities: Document, Chunk
  - infrastructure.db.pool: Connection pool
  - pgvector: Vector extension

Constraints:
  - 768-dimensional embeddings (validated)
  - Statement timeout configured per session

Notes:
  - Implements Repository pattern from domain layer
  - Uses dependency inversion (domain doesn't depend on this)
  - Pool must be initialized before use
"""

from uuid import UUID, uuid4
from typing import List, Optional

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ...domain.entities import Document, Chunk
from ...domain.repositories import DocumentRepository
from ...logger import logger
from ...exceptions import DatabaseError


# R: Expected embedding dimension (Google Gemini)
EMBEDDING_DIMENSION = 768


class PostgresDocumentRepository:
    """
    R: PostgreSQL implementation of DocumentRepository.
    
    Uses connection pool for efficient connection reuse.
    All write operations use transactions for atomicity.
    """
    
    def __init__(self, pool: Optional[ConnectionPool] = None):
        """
        R: Initialize repository with connection pool.
        
        Args:
            pool: Connection pool (if None, uses global pool)
        """
        self._pool = pool
    
    def _get_pool(self) -> ConnectionPool:
        """R: Get pool, falling back to global if not injected."""
        if self._pool is not None:
            return self._pool
        
        from ..db.pool import get_pool
        return get_pool()
    
    def _validate_embeddings(self, chunks: List[Chunk]) -> None:
        """
        R: Validate all chunks have correct embedding dimension.
        
        Raises:
            ValueError: If any embedding has wrong dimension
        """
        for i, chunk in enumerate(chunks):
            if chunk.embedding is None:
                raise ValueError(f"Chunk {i} has no embedding")
            if len(chunk.embedding) != EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Chunk {i} embedding has {len(chunk.embedding)} dimensions, "
                    f"expected {EMBEDDING_DIMENSION}"
                )
    
    def save_document(self, document: Document) -> None:
        """
        R: Persist document metadata to PostgreSQL.
        
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
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
            logger.info(f"PostgresDocumentRepository: Document saved: {document.id}")
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: Failed to save document {document.id}: {e}")
            raise DatabaseError(f"Failed to save document: {e}")
    
    def save_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None:
        """
        R: Persist chunks with embeddings to PostgreSQL (batch insert).
        
        Raises:
            DatabaseError: If database operation fails
            ValueError: If embedding dimension is invalid
        """
        if not chunks:
            return
        
        self._validate_embeddings(chunks)
        
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                # R: Prepare batch data
                batch_data = [
                    (
                        chunk.chunk_id or uuid4(),
                        document_id,
                        chunk.chunk_index or idx,
                        chunk.content,
                        chunk.embedding,
                    )
                    for idx, chunk in enumerate(chunks)
                ]
                
                # R: Batch insert using executemany
                conn.executemany(
                    """
                    INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    batch_data,
                )
            logger.info(f"PostgresDocumentRepository: Saved {len(chunks)} chunks for document {document_id}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: Failed to save chunks for {document_id}: {e}")
            raise DatabaseError(f"Failed to save chunks: {e}")
    
    def save_document_with_chunks(self, document: Document, chunks: List[Chunk]) -> None:
        """
        R: Atomically save document and its chunks in a single transaction.
        
        This is the preferred method for ingestion - ensures no orphan
        documents or partial chunk sets exist.
        
        Args:
            document: Document entity to save
            chunks: List of Chunk entities with embeddings
        
        Raises:
            DatabaseError: If any operation fails (entire transaction rolls back)
            ValueError: If embedding dimension is invalid
        """
        if chunks:
            self._validate_embeddings(chunks)
        
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                # R: Use explicit transaction for atomicity
                with conn.transaction():
                    # R: Insert document
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
                    
                    # R: Batch insert chunks if any
                    if chunks:
                        batch_data = [
                            (
                                chunk.chunk_id or uuid4(),
                                document.id,
                                chunk.chunk_index or idx,
                                chunk.content,
                                chunk.embedding,
                            )
                            for idx, chunk in enumerate(chunks)
                        ]
                        
                        conn.executemany(
                            """
                            INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            batch_data,
                        )
                    
                    # R: Transaction commits here if no exception
            
            logger.info(
                f"PostgresDocumentRepository: Atomic save completed",
                extra={"document_id": str(document.id), "chunks": len(chunks)}
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Atomic save failed, rolled back",
                extra={"document_id": str(document.id), "error": str(e)}
            )
            raise DatabaseError(f"Failed to save document with chunks: {e}")
    
    def find_similar_chunks(
        self,
        embedding: List[float],
        top_k: int
    ) -> List[Chunk]:
        """
        R: Search for similar chunks using vector cosine similarity.
        
        Returns:
            List of Chunk entities ordered by similarity (descending)
        
        Raises:
            DatabaseError: If search query fails
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
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
            logger.info(f"PostgresDocumentRepository: Found {len(rows)} similar chunks")
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: Search failed: {e}")
            raise DatabaseError(f"Search query failed: {e}")
        
        return [
            Chunk(
                chunk_id=r[0],
                document_id=r[1],
                chunk_index=r[2],
                content=r[3],
                embedding=r[4],
                similarity=float(r[5]) if r[5] is not None else None,
            )
            for r in rows
        ]

    def ping(self) -> bool:
        """
        R: Verify database connectivity via pool.

        Returns:
            True if a trivial query succeeds.
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"PostgresDocumentRepository: ping failed: {e}")
            raise DatabaseError(f"Ping failed: {e}")

    def soft_delete_document(self, document_id: UUID) -> bool:
        """
        R: Soft delete a document by setting deleted_at timestamp.
        
        Args:
            document_id: Document UUID to soft delete
        
        Returns:
            True if document was found and deleted, False otherwise
        
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    UPDATE documents
                    SET deleted_at = NOW()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (document_id,),
                )
                deleted = result.rowcount > 0
            if deleted:
                logger.info(f"PostgresDocumentRepository: Soft deleted document {document_id}")
            return deleted
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: Soft delete failed for {document_id}: {e}")
            raise DatabaseError(f"Soft delete failed: {e}")
    
    def restore_document(self, document_id: UUID) -> bool:
        """
        R: Restore a soft-deleted document.
        
        Args:
            document_id: Document UUID to restore
        
        Returns:
            True if document was found and restored, False otherwise
        
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    UPDATE documents
                    SET deleted_at = NULL
                    WHERE id = %s AND deleted_at IS NOT NULL
                    """,
                    (document_id,),
                )
                restored = result.rowcount > 0
            if restored:
                logger.info(f"PostgresDocumentRepository: Restored document {document_id}")
            return restored
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: Restore failed for {document_id}: {e}")
            raise DatabaseError(f"Restore failed: {e}")
