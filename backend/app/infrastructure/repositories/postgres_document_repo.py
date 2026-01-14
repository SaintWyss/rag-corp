"""
Name: PostgreSQL Document Repository Implementation

Responsibilities:
  - Implement DocumentRepository interface for PostgreSQL + pgvector
  - Use connection pool for efficient connection reuse
  - Atomic operations with transactions
  - Batch insert for performance
  - Vector similarity searches using cosine distance
  - Maximal Marginal Relevance (MMR) for diverse retrieval

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
  - MMR balances relevance vs diversity
"""

from uuid import UUID, uuid4
from typing import List, Optional
import numpy as np

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ...domain.entities import Document, Chunk
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
                    (
                        document.id,
                        document.title,
                        document.source,
                        Json(document.metadata),
                    ),
                )
            logger.info(f"PostgresDocumentRepository: Document saved: {document.id}")
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Failed to save document {document.id}: {e}"
            )
            raise DatabaseError(f"Failed to save document: {e}")

    def list_documents(self, limit: int = 50, offset: int = 0) -> List[Document]:
        """
        R: List document metadata ordered by creation time (descending).

        Returns:
            List of Document entities
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, title, source, metadata, created_at, deleted_at
                    FROM documents
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                ).fetchall()

            return [
                Document(
                    id=row[0],
                    title=row[1],
                    source=row[2],
                    metadata=row[3] or {},
                    created_at=row[4],
                    deleted_at=row[5],
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: List documents failed: {e}")
            raise DatabaseError(f"List documents failed: {e}")

    def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        R: Fetch a single document by ID (excluding deleted).

        Returns:
            Document or None if not found
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                row = conn.execute(
                    """
                    SELECT id, title, source, metadata, created_at, deleted_at
                    FROM documents
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (document_id,),
                ).fetchone()

            if not row:
                return None

            return Document(
                id=row[0],
                title=row[1],
                source=row[2],
                metadata=row[3] or {},
                created_at=row[4],
                deleted_at=row[5],
            )
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Get document failed for {document_id}: {e}"
            )
            raise DatabaseError(f"Get document failed: {e}")

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
            logger.info(
                f"PostgresDocumentRepository: Saved {len(chunks)} chunks for document {document_id}"
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Failed to save chunks for {document_id}: {e}"
            )
            raise DatabaseError(f"Failed to save chunks: {e}")

    def save_document_with_chunks(
        self, document: Document, chunks: List[Chunk]
    ) -> None:
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
                        (
                            document.id,
                            document.title,
                            document.source,
                            Json(document.metadata),
                        ),
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
                "PostgresDocumentRepository: Atomic save completed",
                extra={"document_id": str(document.id), "chunks": len(chunks)},
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "PostgresDocumentRepository: Atomic save failed, rolled back",
                extra={"document_id": str(document.id), "error": str(e)},
            )
            raise DatabaseError(f"Failed to save document with chunks: {e}")

    def find_similar_chunks(self, embedding: List[float], top_k: int) -> List[Chunk]:
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
                logger.info(
                    f"PostgresDocumentRepository: Soft deleted document {document_id}"
                )
            return deleted
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Soft delete failed for {document_id}: {e}"
            )
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
                logger.info(
                    f"PostgresDocumentRepository: Restored document {document_id}"
                )
            return restored
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Restore failed for {document_id}: {e}"
            )
            raise DatabaseError(f"Restore failed: {e}")

    def find_similar_chunks_mmr(
        self,
        embedding: List[float],
        top_k: int,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Chunk]:
        """
        R: Search for similar chunks using Maximal Marginal Relevance.

        MMR balances relevance to the query with diversity among results,
        reducing redundant/similar chunks in the output.

        Args:
            embedding: Query embedding vector
            top_k: Number of chunks to return
            fetch_k: Number of candidates to fetch before reranking (should be > top_k)
            lambda_mult: Balance between relevance (1.0) and diversity (0.0)
                        Default 0.5 is a good balance.

        Returns:
            List of Chunk entities ordered by MMR score

        Raises:
            DatabaseError: If search query fails
        """
        # R: Fetch more candidates than needed for MMR selection
        candidates = self.find_similar_chunks(embedding, max(fetch_k, top_k * 2))

        if len(candidates) <= top_k:
            return candidates

        # R: Apply MMR algorithm
        return self._mmr_rerank(embedding, candidates, top_k, lambda_mult)

    def _mmr_rerank(
        self,
        query_embedding: List[float],
        candidates: List[Chunk],
        top_k: int,
        lambda_mult: float,
    ) -> List[Chunk]:
        """
        R: Rerank candidates using Maximal Marginal Relevance algorithm.

        MMR = argmax[λ * sim(d, q) - (1 - λ) * max(sim(d, d_i))]

        Where:
            d = candidate document
            q = query
            d_i = already selected documents
            λ = lambda_mult (relevance vs diversity tradeoff)
        """
        query_vec = np.array(query_embedding)

        # R: Pre-compute candidate embeddings and similarities to query
        candidate_vecs = []
        query_sims = []
        for c in candidates:
            if c.embedding:
                vec = np.array(c.embedding)
                candidate_vecs.append(vec)
                # R: Cosine similarity to query
                query_sims.append(self._cosine_similarity(query_vec, vec))
            else:
                candidate_vecs.append(None)
                query_sims.append(0.0)

        selected_indices: List[int] = []
        selected_vecs: List[np.ndarray] = []

        for _ in range(min(top_k, len(candidates))):
            best_score = -float("inf")
            best_idx = -1

            for i, c in enumerate(candidates):
                if i in selected_indices or candidate_vecs[i] is None:
                    continue

                # R: Relevance term
                relevance = query_sims[i]

                # R: Diversity term (max similarity to already selected)
                diversity_penalty = 0.0
                if selected_vecs:
                    max_sim = max(
                        self._cosine_similarity(candidate_vecs[i], sv)
                        for sv in selected_vecs
                    )
                    diversity_penalty = max_sim

                # R: MMR score
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * diversity_penalty

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            if best_idx >= 0:
                selected_indices.append(best_idx)
                selected_vecs.append(candidate_vecs[best_idx])

        logger.info(
            f"PostgresDocumentRepository: MMR reranked {len(candidates)} → {len(selected_indices)} chunks"
        )

        return [candidates[i] for i in selected_indices]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
