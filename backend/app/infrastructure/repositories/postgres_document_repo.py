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

_DOCUMENT_SORTS = {
    "created_at_desc": "created_at DESC NULLS LAST",
    "created_at_asc": "created_at ASC NULLS LAST",
    "title_asc": "title ASC NULLS LAST",
    "title_desc": "title DESC NULLS LAST",
}


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
                    INSERT INTO documents (
                        id,
                        workspace_id,
                        title,
                        source,
                        metadata,
                        tags,
                        allowed_roles
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET workspace_id = EXCLUDED.workspace_id,
                        title = EXCLUDED.title,
                        source = EXCLUDED.source,
                        metadata = EXCLUDED.metadata,
                        tags = EXCLUDED.tags,
                        allowed_roles = EXCLUDED.allowed_roles
                    """,
                    (
                        document.id,
                        document.workspace_id,
                        document.title,
                        document.source,
                        Json(document.metadata),
                        document.tags or [],
                        document.allowed_roles or [],
                    ),
                )
            logger.info(f"PostgresDocumentRepository: Document saved: {document.id}")
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Failed to save document {document.id}: {e}"
            )
            raise DatabaseError(f"Failed to save document: {e}")

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
        workspace_id: UUID | None = None,
        query: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> List[Document]:
        """
        R: List document metadata ordered by creation time (descending).

        Returns:
            List of Document entities
        """
        try:
            pool = self._get_pool()
            filters = ["deleted_at IS NULL"]
            params: list[object] = []

            if workspace_id is not None:
                filters.append("workspace_id = %s")
                params.append(workspace_id)

            if query:
                like_query = f"%{query}%"
                filters.append(
                    "(title ILIKE %s OR source ILIKE %s OR file_name ILIKE %s OR metadata::text ILIKE %s)"
                )
                params.extend([like_query, like_query, like_query, like_query])

            if status:
                filters.append("status = %s")
                params.append(status)

            if tag:
                filters.append("%s = ANY(tags)")
                params.append(tag)

            order_by = _DOCUMENT_SORTS.get(
                sort or "created_at_desc", _DOCUMENT_SORTS["created_at_desc"]
            )
            where_clause = " AND ".join(filters)

            with pool.connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, workspace_id, title, source, metadata, created_at, deleted_at,
                           file_name, mime_type, storage_key,
                           uploaded_by_user_id, status, error_message, tags, allowed_roles
                    FROM documents
                    WHERE {where_clause}
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s
                    """,
                    (*params, limit, offset),
                ).fetchall()

            return [
                Document(
                    id=row[0],
                    workspace_id=row[1],
                    title=row[2],
                    source=row[3],
                    metadata=row[4] or {},
                    created_at=row[5],
                    deleted_at=row[6],
                    file_name=row[7],
                    mime_type=row[8],
                    storage_key=row[9],
                    uploaded_by_user_id=row[10],
                    status=row[11],
                    error_message=row[12],
                    tags=row[13] or [],
                    allowed_roles=row[14] or [],
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"PostgresDocumentRepository: List documents failed: {e}")
            raise DatabaseError(f"List documents failed: {e}")

    def get_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> Optional[Document]:
        """
        R: Fetch a single document by ID (excluding deleted).

        Returns:
            Document or None if not found
        """
        try:
            pool = self._get_pool()
            query = """
                SELECT id, workspace_id, title, source, metadata, created_at, deleted_at,
                       file_name, mime_type, storage_key,
                       uploaded_by_user_id, status, error_message, tags, allowed_roles
                FROM documents
                WHERE id = %s AND deleted_at IS NULL
            """
            params: list[object] = [document_id]
            if workspace_id is not None:
                query += " AND workspace_id = %s"
                params.append(workspace_id)

            with pool.connection() as conn:
                row = conn.execute(query, params).fetchone()

            if not row:
                return None

            return Document(
                id=row[0],
                workspace_id=row[1],
                title=row[2],
                source=row[3],
                metadata=row[4] or {},
                created_at=row[5],
                deleted_at=row[6],
                file_name=row[7],
                mime_type=row[8],
                storage_key=row[9],
                uploaded_by_user_id=row[10],
                status=row[11],
                error_message=row[12],
                tags=row[13] or [],
                allowed_roles=row[14] or [],
            )
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Get document failed for {document_id}: {e}"
            )
            raise DatabaseError(f"Get document failed: {e}")

    def save_chunks(
        self,
        document_id: UUID,
        chunks: List[Chunk],
        *,
        workspace_id: UUID | None = None,
    ) -> None:
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
                if workspace_id is not None:
                    row = conn.execute(
                        """
                        SELECT 1
                        FROM documents
                        WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL
                        """,
                        (document_id, workspace_id),
                    ).fetchone()
                    if not row:
                        raise DatabaseError(
                            f"Document {document_id} not found for workspace {workspace_id}"
                        )
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
        except DatabaseError:
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
                        INSERT INTO documents (
                            id,
                            workspace_id,
                            title,
                            source,
                            metadata,
                            tags,
                            allowed_roles
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET workspace_id = EXCLUDED.workspace_id,
                            title = EXCLUDED.title,
                            source = EXCLUDED.source,
                            metadata = EXCLUDED.metadata,
                            tags = EXCLUDED.tags,
                            allowed_roles = EXCLUDED.allowed_roles
                        """,
                        (
                            document.id,
                            document.workspace_id,
                            document.title,
                            document.source,
                            Json(document.metadata),
                            document.tags or [],
                            document.allowed_roles or [],
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

    def update_document_file_metadata(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        storage_key: str | None = None,
        uploaded_by_user_id: UUID | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        R: Update file metadata for a document.

        Returns True if a document was updated, otherwise False.
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                query = """
                    UPDATE documents
                    SET file_name = %s,
                        mime_type = %s,
                        storage_key = %s,
                        uploaded_by_user_id = %s,
                        status = %s,
                        error_message = %s
                    WHERE id = %s
                """
                params: list[object] = [
                    file_name,
                    mime_type,
                    storage_key,
                    uploaded_by_user_id,
                    status,
                    error_message,
                    document_id,
                ]
                if workspace_id is not None:
                    query += " AND workspace_id = %s"
                    params.append(workspace_id)
                result = conn.execute(query, params)
            return result.rowcount > 0
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Update file metadata failed: {e}"
            )
            raise DatabaseError(f"Failed to update file metadata: {e}")

    def transition_document_status(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        from_statuses: list[str | None],
        to_status: str,
        error_message: str | None = None,
    ) -> bool:
        """
        R: Update status if current status is in allowed set.

        Returns True if a document was updated, otherwise False.
        """
        if not from_statuses:
            return False

        include_null = any(status is None for status in from_statuses)
        allowed_statuses = [status for status in from_statuses if status is not None]

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                query = """
                    UPDATE documents
                    SET status = %s,
                        error_message = %s
                    WHERE id = %s
                """
                params: list[object] = [to_status, error_message, document_id]

                if workspace_id is not None:
                    query += " AND workspace_id = %s"
                    params.append(workspace_id)

                if allowed_statuses and include_null:
                    query += " AND (status = ANY(%s) OR status IS NULL)"
                    params.append(allowed_statuses)
                elif allowed_statuses:
                    query += " AND status = ANY(%s)"
                    params.append(allowed_statuses)
                elif include_null:
                    query += " AND status IS NULL"

                result = conn.execute(query, params)
            return result.rowcount > 0
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Status transition failed: {e}"
            )
            raise DatabaseError(f"Failed to transition status: {e}")

    def delete_chunks_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        """R: Delete all chunks for a document."""
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                if workspace_id is not None:
                    result = conn.execute(
                        """
                        DELETE FROM chunks c
                        USING documents d
                        WHERE c.document_id = d.id
                          AND c.document_id = %s
                          AND d.workspace_id = %s
                        """,
                        (document_id, workspace_id),
                    )
                else:
                    result = conn.execute(
                        "DELETE FROM chunks WHERE document_id = %s",
                        (document_id,),
                    )
            return result.rowcount
        except Exception as e:
            logger.error(
                f"PostgresDocumentRepository: Delete chunks failed for {document_id}: {e}"
            )
            raise DatabaseError(f"Failed to delete chunks: {e}")

    def find_similar_chunks(
        self,
        embedding: List[float],
        top_k: int,
        *,
        workspace_id: UUID | None = None,
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
            filters = ["d.deleted_at IS NULL"]
            params: list[object] = []

            if workspace_id is not None:
                filters.append("d.workspace_id = %s")
                params.append(workspace_id)

            where_clause = " AND ".join(filters)
            with pool.connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                      c.id,
                      c.document_id,
                      c.chunk_index,
                      c.content,
                      c.embedding,
                      (1 - (c.embedding <=> %s::vector)) as score
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE {where_clause}
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, *params, embedding, top_k),
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

    def soft_delete_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
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
                query = """
                    UPDATE documents
                    SET deleted_at = NOW()
                    WHERE id = %s AND deleted_at IS NULL
                """
                params: list[object] = [document_id]
                if workspace_id is not None:
                    query += " AND workspace_id = %s"
                    params.append(workspace_id)
                result = conn.execute(query, params)
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

    def restore_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
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
                query = """
                    UPDATE documents
                    SET deleted_at = NULL
                    WHERE id = %s AND deleted_at IS NOT NULL
                """
                params: list[object] = [document_id]
                if workspace_id is not None:
                    query += " AND workspace_id = %s"
                    params.append(workspace_id)
                result = conn.execute(query, params)
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
        *,
        workspace_id: UUID | None = None,
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
        candidates = self.find_similar_chunks(
            embedding,
            max(fetch_k, top_k * 2),
            workspace_id=workspace_id,
        )

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
