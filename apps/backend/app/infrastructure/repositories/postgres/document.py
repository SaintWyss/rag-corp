"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres_document_repo.py
============================================================
Class: PostgresDocumentRepository

Responsibilities:
- Implementar el repositorio de documentos y chunks sobre PostgreSQL + pgvector.
- Operaciones de escritura atómicas mediante transacciones (evitar estados parciales).
- Inserción batch de chunks (performance / menos round-trips).
- Búsqueda vectorial por similitud (cosine distance) usando pgvector.
- Re-ranking opcional con MMR (diversidad vs relevancia).

Collaborators:
- domain.entities: Document, Chunk
- infrastructure.db.pool: get_pool() (ConnectionPool)
- psycopg / psycopg_pool: ejecución SQL y pooling
- pgvector: tipo vector + operador <=> (distancia)
- crosscutting.logger / crosscutting.exceptions

Constraints / Notes (Clean / KISS):
- Este archivo es “infra”: NO contiene políticas de negocio (RBAC/ACL/visibilidad).
- Todas las queries son parametrizadas (no interpolar input de usuario).
- `workspace_id` es un boundary: se exige para evitar accesos cross-scope.
- Dimensión de embeddings fija (768) y validada al persistir chunks.
============================================================
"""

from __future__ import annotations

from typing import Iterable
from uuid import UUID, uuid4

import numpy as np
from psycopg.errors import DuplicatePreparedStatement
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....domain.entities import Chunk, Document, Node

# ============================================================
# Constantes de contrato (DB / embeddings)
# ============================================================

# Dimensión esperada del embedding (debe matchear chunks.embedding vector(768))
EMBEDDING_DIMENSION = 768

# Allowlist de ORDER BY: evita inyección y mantiene un contrato estable de sorting.
_DOCUMENT_SORTS: dict[str, str] = {
    "created_at_desc": "created_at DESC NULLS LAST",
    "created_at_asc": "created_at ASC NULLS LAST",
    "title_asc": "title ASC NULLS LAST",
    "title_desc": "title DESC NULLS LAST",
}


class PostgresDocumentRepository:
    """
    Repositorio PostgreSQL para Documentos + Chunks.

    Modelo mental:
    - documents: metadata + estado del pipeline (status, error_message, file_*, etc.)
    - chunks: contenido segmentado + embedding vectorial para retrieval
    """

    # ---------------------------------------------------------------------
    # SQL SELECT “canon” (misma proyección => mapeo consistente)
    # ---------------------------------------------------------------------
    _DOC_SELECT_COLUMNS = """
        id, workspace_id, title, source, metadata, created_at, deleted_at,
        file_name, mime_type, storage_key,
        uploaded_by_user_id, status, error_message, tags, allowed_roles,
        content_hash
    """

    def __init__(self, pool: ConnectionPool | None = None):
        # Pool inyectable: tests pueden usar un pool controlado o fake.
        self._pool = pool

    # ============================================================
    # Pool / Scope guards
    # ============================================================
    def _get_pool(self) -> ConnectionPool:
        """Devuelve el pool inyectado o el pool global (lazy import)."""
        if self._pool is not None:
            return self._pool

        from app.infrastructure.db.pool import get_pool

        return get_pool()

    def _require_workspace_id(self, workspace_id: UUID | None, action: str) -> UUID:
        """
        Guard clause: obliga scoping por workspace.

        Por qué:
        - Evita consultas “cross-scope” accidentales.
        - Hace explícito el boundary de multi-tenant.
        """
        if workspace_id is None:
            # Métrica opcional (no rompemos si no existe).
            try:
                from ....crosscutting.metrics import record_cross_scope_block

                record_cross_scope_block()
            except Exception:
                pass

            logger.warning(
                "PostgresDocumentRepository: workspace_id required",
                extra={"action": action},
            )
            raise DatabaseError(f"workspace_id is required for {action}")

        return workspace_id

    # ============================================================
    # Validaciones (contrato embedding)
    # ============================================================
    def _validate_embedding(self, embedding: list[float] | None, *, ctx: str) -> None:
        """Valida existencia y dimensión del embedding."""
        if embedding is None:
            raise ValueError(f"{ctx}: embedding is required")
        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"{ctx}: embedding has {len(embedding)} dimensions, expected {EMBEDDING_DIMENSION}"
            )

    def _validate_embeddings(self, chunks: list[Chunk]) -> None:
        """Valida embeddings de todos los chunks (fail fast)."""
        for i, chunk in enumerate(chunks):
            self._validate_embedding(
                chunk.embedding,
                ctx=f"Chunk[{i}]",
            )

    def _validate_node_embeddings(self, nodes: list[Node]) -> None:
        """Valida embeddings de todos los nodos (fail fast)."""
        for i, node in enumerate(nodes):
            self._validate_embedding(
                node.embedding,
                ctx=f"Node[{i}]",
            )

    # ============================================================
    # Helpers DB (DRY: logging + exception wrapping consistente)
    # ============================================================
    def _fetchall(
        self,
        *,
        query: str,
        params: Iterable[object],
        context_msg: str,
        extra: dict,
    ) -> list[tuple]:
        """Ejecuta SELECT y devuelve todas las filas."""
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchall()
        except Exception as exc:
            logger.exception(context_msg, extra={**extra, "error": str(exc)})
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    def _fetchone(
        self,
        *,
        query: str,
        params: Iterable[object],
        context_msg: str,
        extra: dict,
    ) -> tuple | None:
        """Ejecuta SELECT y devuelve una fila o None."""
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchone()
        except Exception as exc:
            logger.exception(context_msg, extra={**extra, "error": str(exc)})
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    # ============================================================
    # Mapping (SQL row -> entidades)
    # ============================================================
    def _row_to_document(self, row: tuple) -> Document:
        """
        Mapea un row de documents al entity Document.

        Mantener esta función “única” reduce bugs por desalineación de columnas.
        """
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
            content_hash=row[15] if len(row) > 15 else None,
        )

    def _rows_to_documents(self, rows: list[tuple]) -> list[Document]:
        """Helper de conversión masiva (list comprehension limpia)."""
        return [self._row_to_document(r) for r in rows]

    # ============================================================
    # Persistencia de Document (metadata)
    # ============================================================
    def save_document(self, document: Document) -> None:
        """
        Upsert de documento (metadata/estado).

        - Requiere workspace_id (scope).
        - ON CONFLICT (id): actualiza campos relevantes.
        - No maneja chunks (eso va por save_chunks / save_document_with_chunks).
        """
        workspace_id = self._require_workspace_id(
            document.workspace_id, "save_document"
        )

        query = """
            INSERT INTO documents (
                id,
                workspace_id,
                title,
                source,
                metadata,
                tags,
                allowed_roles,
                content_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET workspace_id = EXCLUDED.workspace_id,
                title = EXCLUDED.title,
                source = EXCLUDED.source,
                metadata = EXCLUDED.metadata,
                tags = EXCLUDED.tags,
                allowed_roles = EXCLUDED.allowed_roles,
                content_hash = EXCLUDED.content_hash
        """

        params = (
            document.id,
            workspace_id,
            document.title,
            document.source,
            Json(document.metadata),
            document.tags or [],
            document.allowed_roles or [],
            document.content_hash,
        )

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(query, params)
            logger.info(
                "PostgresDocumentRepository: Document saved",
                extra={"document_id": str(document.id)},
            )
        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Failed to save document",
                extra={"document_id": str(document.id), "error": str(exc)},
            )
            raise DatabaseError(f"Failed to save document: {exc}") from exc

    # ============================================================
    # Listado / Lectura de documents
    # ============================================================
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
    ) -> list[Document]:
        """
        Lista documentos (metadata) por workspace, excluyendo soft-deleted.

        Filtros soportados:
        - query: búsqueda textual (title/source/file_name/metadata::text)
        - status: estado del pipeline
        - tag: pertenencia a tags (ANY(tags))

        Sorting:
        - allowlist (_DOCUMENT_SORTS) => evita inyección y mantiene API estable.
        """
        scoped_workspace_id = self._require_workspace_id(workspace_id, "list_documents")

        # Guard rails básicos (evitan parámetros absurdos).
        if limit <= 0:
            return []
        if offset < 0:
            offset = 0

        filters: list[str] = ["deleted_at IS NULL", "workspace_id = %s"]
        params: list[object] = [scoped_workspace_id]

        if query:
            # ILIKE es case-insensitive.
            like = f"%{query}%"
            filters.append(
                "(title ILIKE %s OR source ILIKE %s OR file_name ILIKE %s OR metadata::text ILIKE %s)"
            )
            params.extend([like, like, like, like])

        if status:
            filters.append("status = %s")
            params.append(status)

        if tag:
            filters.append("%s = ANY(tags)")
            params.append(tag)

        where_clause = " AND ".join(filters)

        order_by = _DOCUMENT_SORTS.get(
            sort or "created_at_desc", _DOCUMENT_SORTS["created_at_desc"]
        )

        sql = f"""
            SELECT {self._DOC_SELECT_COLUMNS}
            FROM documents
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """

        rows = self._fetchall(
            query=sql,
            params=[*params, limit, offset],
            context_msg="PostgresDocumentRepository: List documents failed",
            extra={
                "workspace_id": str(scoped_workspace_id),
                "sort": sort or "created_at_desc",
            },
        )

        return self._rows_to_documents(rows)

    def get_document(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> Document | None:
        """
        Obtiene un documento por ID (scoped por workspace) excluyendo deleted.

        Retorna:
        - Document si existe y no está borrado
        - None si no existe (o si está soft-deleted)
        """
        scoped_workspace_id = self._require_workspace_id(workspace_id, "get_document")

        row = self._fetchone(
            query=f"""
                SELECT {self._DOC_SELECT_COLUMNS}
                FROM documents
                WHERE id = %s
                  AND workspace_id = %s
                  AND deleted_at IS NULL
            """,
            params=[document_id, scoped_workspace_id],
            context_msg="PostgresDocumentRepository: Get document failed",
            extra={
                "document_id": str(document_id),
                "workspace_id": str(scoped_workspace_id),
            },
        )

        return None if not row else self._row_to_document(row)

    def get_document_by_content_hash(
        self, workspace_id: UUID, content_hash: str
    ) -> Document | None:
        """
        Busca documento por hash de contenido dentro de un workspace.

        Retorna:
        - Document si existe un documento activo con ese hash
        - None si no existe (o si está soft-deleted)
        """
        row = self._fetchone(
            query=f"""
                SELECT {self._DOC_SELECT_COLUMNS}
                FROM documents
                WHERE workspace_id = %s
                  AND content_hash = %s
                  AND deleted_at IS NULL
            """,
            params=[workspace_id, content_hash],
            context_msg="PostgresDocumentRepository: Get document by content hash failed",
            extra={
                "workspace_id": str(workspace_id),
                "content_hash": content_hash[:8],
            },
        )

        return None if not row else self._row_to_document(row)

    # ============================================================
    # Persistencia de Chunks
    # ============================================================
    # Chunk persistence (batch)
    # ============================================================
    def _lookup_workspace_fts_language(self, conn, workspace_id: UUID) -> str:
        """Obtiene fts_language del workspace. Fallback a 'spanish'."""
        row = conn.execute(
            "SELECT COALESCE(w.fts_language, 'spanish') FROM workspaces w WHERE w.id = %s",
            (workspace_id,),
        ).fetchone()
        return row[0] if row else "spanish"

    def save_chunks(
        self,
        document_id: UUID,
        chunks: list[Chunk],
        *,
        workspace_id: UUID | None = None,
    ) -> None:
        """
        Inserta chunks para un documento (batch insert).

        - Valida embeddings (dimensión).
        - Verifica que el documento exista en el workspace y no esté deleted.
        - Inserta N chunks con executemany (performance).
        """
        if not chunks:
            return

        scoped_workspace_id = self._require_workspace_id(workspace_id, "save_chunks")
        self._validate_embeddings(chunks)

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                # 1) Verificación de existencia del documento (scope + no deleted)
                exists = conn.execute(
                    """
                    SELECT 1
                    FROM documents
                    WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL
                    """,
                    (document_id, scoped_workspace_id),
                ).fetchone()

                if not exists:
                    raise DatabaseError(
                        f"Document {document_id} not found for workspace {scoped_workspace_id}"
                    )

                # 2) Lookup workspace fts_language
                fts_lang = self._lookup_workspace_fts_language(conn, scoped_workspace_id)

                # 3) Preparación del batch (cada fila corresponde a un INSERT)
                batch = [
                    (
                        chunk.chunk_id or uuid4(),
                        document_id,
                        chunk.chunk_index if chunk.chunk_index is not None else idx,
                        chunk.content,
                        chunk.embedding,  # pgvector acepta lista/array
                        Json(chunk.metadata or {}),
                        fts_lang,
                        chunk.content,
                    )
                    for idx, chunk in enumerate(chunks)
                ]

                # 4) Inserción batch (con fallback por colisiones de prepared statements).
                with conn.cursor() as cur:
                    try:
                        cur.executemany(
                            """
                            INSERT INTO chunks (id, document_id, chunk_index, content, embedding, metadata, tsv)
                            VALUES (%s, %s, %s, %s, %s, %s, to_tsvector(%s::regconfig, coalesce(%s, '')))
                            """,
                            batch,
                        )
                    except DuplicatePreparedStatement:
                        # Fallback defensivo: desactivamos batch si el driver choca en prepared statements.
                        conn.rollback()
                        for row in batch:
                            conn.execute(
                                """
                                INSERT INTO chunks (id, document_id, chunk_index, content, embedding, metadata, tsv)
                                VALUES (%s, %s, %s, %s, %s, %s, to_tsvector(%s::regconfig, coalesce(%s, '')))
                                """,
                                row,
                            )

            logger.info(
                "PostgresDocumentRepository: Saved chunks",
                extra={"document_id": str(document_id), "count": len(chunks)},
            )

        except ValueError:
            # Propagamos tal cual: es error de contrato (embedding inválido)
            raise
        except DatabaseError:
            raise
        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Failed to save chunks",
                extra={"document_id": str(document_id), "error": str(exc)},
            )
            raise DatabaseError(f"Failed to save chunks: {exc}") from exc

    def save_document_with_chunks(
        self, document: Document, chunks: list[Chunk], nodes: list[Node] | None = None
    ) -> None:
        """
        Guardado atómico: documento + chunks (+ nodos opcionales) en una misma transacción.

        Qué garantiza:
        - No quedan "documents sin chunks" por fallos intermedios.
        - No quedan "chunks huérfanos" sin documento.
        - Si se pasan nodos, se persisten en la misma transacción.
        """
        workspace_id = self._require_workspace_id(
            document.workspace_id, "save_document_with_chunks"
        )
        if chunks:
            self._validate_embeddings(chunks)
        if nodes:
            self._validate_node_embeddings(nodes)

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                with conn.transaction():
                    # 1) Upsert del documento
                    conn.execute(
                        """
                        INSERT INTO documents (
                            id,
                            workspace_id,
                            title,
                            source,
                            metadata,
                            tags,
                            allowed_roles,
                            content_hash
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET workspace_id = EXCLUDED.workspace_id,
                            title = EXCLUDED.title,
                            source = EXCLUDED.source,
                            metadata = EXCLUDED.metadata,
                            tags = EXCLUDED.tags,
                            allowed_roles = EXCLUDED.allowed_roles,
                            content_hash = EXCLUDED.content_hash
                        """,
                        (
                            document.id,
                            workspace_id,
                            document.title,
                            document.source,
                            Json(document.metadata),
                            document.tags or [],
                            document.allowed_roles or [],
                            document.content_hash,
                        ),
                    )

                    # 2) Inserción de chunks (si hay)
                    if chunks:
                        fts_lang = self._lookup_workspace_fts_language(conn, workspace_id)
                        batch = [
                            (
                                chunk.chunk_id or uuid4(),
                                document.id,
                                (
                                    chunk.chunk_index
                                    if chunk.chunk_index is not None
                                    else idx
                                ),
                                chunk.content,
                                chunk.embedding,
                                Json(chunk.metadata or {}),
                                fts_lang,
                                chunk.content,
                            )
                            for idx, chunk in enumerate(chunks)
                        ]

                        with conn.cursor() as cur:
                            cur.executemany(
                                """
                                INSERT INTO chunks (id, document_id, chunk_index, content, embedding, metadata, tsv)
                                VALUES (%s, %s, %s, %s, %s, %s, to_tsvector(%s::regconfig, coalesce(%s, '')))
                                """,
                                batch,
                            )

                    # 3) Inserción de nodos (si hay)
                    if nodes:
                        node_batch = [
                            (
                                node.node_id or uuid4(),
                                workspace_id,
                                document.id,
                                node.node_index if node.node_index is not None else idx,
                                node.node_text,
                                node.span_start,
                                node.span_end,
                                node.embedding,
                                Json(node.metadata or {}),
                            )
                            for idx, node in enumerate(nodes)
                        ]

                        with conn.cursor() as cur:
                            cur.executemany(
                                """
                                INSERT INTO nodes (
                                    id, workspace_id, document_id, node_index,
                                    node_text, span_start, span_end, embedding, metadata
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                node_batch,
                            )

            logger.info(
                "PostgresDocumentRepository: Atomic save completed",
                extra={"document_id": str(document.id), "chunks": len(chunks)},
            )

        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Atomic save failed (rolled back)",
                extra={"document_id": str(document.id), "error": str(exc)},
            )
            raise DatabaseError(f"Failed to save document with chunks: {exc}") from exc

    # ============================================================
    # Update metadata / status (pipeline)
    # ============================================================
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
        Actualiza metadata de archivo y estado.

        Retorna:
        - True si se actualizó una fila
        - False si no existe (o no matchea el workspace)
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "update_document_file_metadata"
        )

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    UPDATE documents
                    SET file_name = %s,
                        mime_type = %s,
                        storage_key = %s,
                        uploaded_by_user_id = %s,
                        status = %s,
                        error_message = %s
                    WHERE id = %s AND workspace_id = %s
                    """,
                    (
                        file_name,
                        mime_type,
                        storage_key,
                        uploaded_by_user_id,
                        status,
                        error_message,
                        document_id,
                        scoped_workspace_id,
                    ),
                )
            return bool(result.rowcount and result.rowcount > 0)

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Update file metadata failed",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Failed to update file metadata: {exc}") from exc

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
        Transición de estado condicional (optimistic):

        - Solo actualiza si el status actual está en from_statuses.
        - from_statuses puede incluir None (status IS NULL).

        Retorna True si se actualizó; False si no (status no permitido o no existe).
        """
        if not from_statuses:
            return False

        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "transition_document_status"
        )

        include_null = any(s is None for s in from_statuses)
        allowed = [s for s in from_statuses if s is not None]

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                sql = """
                    UPDATE documents
                    SET status = %s,
                        error_message = %s
                    WHERE id = %s AND workspace_id = %s
                """
                params: list[object] = [
                    to_status,
                    error_message,
                    document_id,
                    scoped_workspace_id,
                ]

                # Construcción controlada (no hay input directo: allowed viene de la app)
                if allowed and include_null:
                    sql += " AND (status = ANY(%s) OR status IS NULL)"
                    params.append(allowed)
                elif allowed:
                    sql += " AND status = ANY(%s)"
                    params.append(allowed)
                elif include_null:
                    sql += " AND status IS NULL"

                result = conn.execute(sql, params)

            return bool(result.rowcount and result.rowcount > 0)

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Status transition failed",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Failed to transition status: {exc}") from exc

    # ============================================================
    # Deletes / Restore
    # ============================================================
    def delete_chunks_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        """
        Borra chunks de un documento (scoped por workspace vía join).

        Retorna cantidad de filas eliminadas.
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "delete_chunks_for_document"
        )

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    DELETE FROM chunks c
                    USING documents d
                    WHERE c.document_id = d.id
                      AND c.document_id = %s
                      AND d.workspace_id = %s
                    """,
                    (document_id, scoped_workspace_id),
                )
            return int(result.rowcount or 0)

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Delete chunks failed",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Failed to delete chunks: {exc}") from exc

    def soft_delete_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
        """
        Soft delete: set deleted_at = NOW() si aún no estaba borrado.
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "soft_delete_document"
        )

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    UPDATE documents
                    SET deleted_at = NOW()
                    WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL
                    """,
                    (document_id, scoped_workspace_id),
                )

            deleted = bool(result.rowcount and result.rowcount > 0)
            if deleted:
                logger.info(
                    "PostgresDocumentRepository: Soft deleted document",
                    extra={"document_id": str(document_id)},
                )
            return deleted

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Soft delete failed",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Soft delete failed: {exc}") from exc

    def soft_delete_documents_by_workspace(self, workspace_id: UUID) -> int:
        """
        Soft delete masivo por workspace (sin scope adicional).
        Retorna cantidad de documents marcados.
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    UPDATE documents
                    SET deleted_at = NOW()
                    WHERE workspace_id = %s AND deleted_at IS NULL
                    """,
                    (workspace_id,),
                )
            return int(result.rowcount or 0)

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Workspace soft delete failed",
                extra={"workspace_id": str(workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"Workspace soft delete failed: {exc}") from exc

    def restore_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
        """
        Restaura un documento soft-deleted (deleted_at -> NULL).
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "restore_document"
        )

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    UPDATE documents
                    SET deleted_at = NULL
                    WHERE id = %s AND workspace_id = %s AND deleted_at IS NOT NULL
                    """,
                    (document_id, scoped_workspace_id),
                )

            restored = bool(result.rowcount and result.rowcount > 0)
            if restored:
                logger.info(
                    "PostgresDocumentRepository: Restored document",
                    extra={"document_id": str(document_id)},
                )
            return restored

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Restore failed",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Restore failed: {exc}") from exc

    # ============================================================
    # Full-text search (tsvector + GIN)
    # ============================================================
    def find_chunks_full_text(
        self,
        query_text: str,
        top_k: int,
        *,
        workspace_id: UUID | None = None,
        fts_language: str = "spanish",
    ) -> list[Chunk]:
        """
        Búsqueda full-text (sparse) usando tsvector + ts_rank_cd.

        - Usa la columna `tsv` computada al INSERT con to_tsvector(lang, content).
        - Operador @@: match full-text.
        - websearch_to_tsquery: parseo robusto de queries de usuario
          (soporta operadores OR, -, "frase exacta", etc.).
        - ts_rank_cd: ranking por cobertura de documento (cover density).
        - fts_language: idioma del workspace (parametrizado vía %s::regconfig).
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "find_chunks_full_text"
        )

        if top_k <= 0 or not (query_text or "").strip():
            return []

        # Validar idioma contra allowlist del dominio (doble barrera).
        from ....domain.entities import validate_fts_language

        safe_lang = validate_fts_language(fts_language)

        sql = """
            SELECT
              c.id,
              c.document_id,
              d.title,
              d.source,
              c.chunk_index,
              c.content,
              c.embedding,
              c.metadata,
              ts_rank_cd(c.tsv, websearch_to_tsquery(%s::regconfig, %s)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.deleted_at IS NULL
              AND d.workspace_id = %s
              AND c.tsv @@ websearch_to_tsquery(%s::regconfig, %s)
            ORDER BY score DESC
            LIMIT %s
        """

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(
                    sql,
                    (safe_lang, query_text, scoped_workspace_id, safe_lang, query_text, top_k),
                ).fetchall()

            logger.info(
                "PostgresDocumentRepository: Full-text search completed",
                extra={
                    "workspace_id": str(scoped_workspace_id),
                    "count": len(rows),
                    "top_k": top_k,
                },
            )

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Full-text search failed",
                extra={
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Full-text search failed: {exc}") from exc

        return [
            Chunk(
                chunk_id=r[0],
                document_id=r[1],
                document_title=r[2],
                document_source=r[3],
                chunk_index=r[4],
                content=r[5],
                embedding=r[6],
                metadata=r[7] or {},
                similarity=float(r[8]) if r[8] is not None else None,
            )
            for r in rows
        ]

    # ============================================================
    # Vector search (pgvector)
    # ============================================================
    def find_similar_chunks(
        self,
        embedding: list[float],
        top_k: int,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """
        Búsqueda vectorial por similitud (cosine distance).

        - Usa operador <=> de pgvector:
            ORDER BY embedding <=> query_vector  (menor distancia = mejor)
        - Score aproximado:
            score = 1 - distance
          (útil para ranking/telemetría; no es “probabilidad”)
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "find_similar_chunks"
        )
        self._validate_embedding(embedding, ctx="Query")

        if top_k <= 0:
            return []

        # Filtro base: solo documentos vivos y del workspace
        where_clause = "d.deleted_at IS NULL AND d.workspace_id = %s"

        sql = f"""
            SELECT
              c.id,
              c.document_id,
              d.title,
              d.source,
              c.chunk_index,
              c.content,
              c.embedding,
              c.metadata,
              (1 - (c.embedding <=> %s::vector)) as score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE {where_clause}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(
                    sql,
                    (embedding, scoped_workspace_id, embedding, top_k),
                ).fetchall()

            logger.info(
                "PostgresDocumentRepository: Similar chunks retrieved",
                extra={
                    "workspace_id": str(scoped_workspace_id),
                    "count": len(rows),
                    "top_k": top_k,
                },
            )

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Search query failed",
                extra={"workspace_id": str(scoped_workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"Search query failed: {exc}") from exc

        # Mapeo a Chunk: incluye datos del documento para contexto en RAG
        return [
            Chunk(
                chunk_id=r[0],
                document_id=r[1],
                document_title=r[2],
                document_source=r[3],
                chunk_index=r[4],
                content=r[5],
                embedding=r[6],
                metadata=r[7] or {},
                similarity=float(r[8]) if r[8] is not None else None,
            )
            for r in rows
        ]

    def find_similar_chunks_mmr(
        self,
        embedding: list[float],
        top_k: int,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """
        Vector search + MMR (Maximal Marginal Relevance).

        Idea:
        - Primero buscamos candidatos por similitud (fetch_k).
        - Luego re-rankeamos para reducir redundancia (diversidad).

        Parámetros:
        - lambda_mult: 1.0 => solo relevancia, 0.0 => solo diversidad.
        """
        self._validate_embedding(embedding, ctx="Query")

        if top_k <= 0:
            return []

        # Aseguramos un pool razonable de candidatos
        effective_fetch = max(fetch_k, top_k * 2)

        candidates = self.find_similar_chunks(
            embedding=embedding,
            top_k=effective_fetch,
            workspace_id=workspace_id,
        )

        if len(candidates) <= top_k:
            return candidates

        return self._mmr_rerank(
            query_embedding=embedding,
            candidates=candidates,
            top_k=top_k,
            lambda_mult=lambda_mult,
        )

    # ============================================================
    # MMR (algoritmo local) — se mantiene privado para no “ensuciar” la capa pública
    # ============================================================
    def _mmr_rerank(
        self,
        query_embedding: list[float],
        candidates: list[Chunk],
        top_k: int,
        lambda_mult: float,
    ) -> list[Chunk]:
        """
        Re-ranking con MMR:

        score(d) = λ * sim(d, q) - (1-λ) * max(sim(d, d_i))
        - sim: cosine similarity
        - q: query
        - d_i: elementos ya seleccionados

        Esto evita devolver chunks casi idénticos cuando el embedding captura la misma idea.
        """
        q = np.array(query_embedding, dtype=float)

        # Precomputamos vectores candidatos y similitud a la query
        cand_vecs: list[np.ndarray] = []
        query_sims: list[float] = []
        for c in candidates:
            emb = c.embedding or []
            if len(emb) != EMBEDDING_DIMENSION:
                # Si algo raro entró, lo tratamos como “no elegible”
                cand_vecs.append(np.zeros(EMBEDDING_DIMENSION))
                query_sims.append(0.0)
                continue

            v = np.array(emb, dtype=float)
            cand_vecs.append(v)
            query_sims.append(self._cosine_similarity(q, v))

        selected: list[int] = []
        selected_vecs: list[np.ndarray] = []

        for _ in range(min(top_k, len(candidates))):
            best_idx = -1
            best_score = -float("inf")

            for i in range(len(candidates)):
                if i in selected:
                    continue

                relevance = query_sims[i]

                # Penalización por redundancia con lo ya seleccionado
                diversity_penalty = 0.0
                if selected_vecs:
                    diversity_penalty = max(
                        self._cosine_similarity(cand_vecs[i], sv)
                        for sv in selected_vecs
                    )

                mmr = lambda_mult * relevance - (1.0 - lambda_mult) * diversity_penalty
                if mmr > best_score:
                    best_score = mmr
                    best_idx = i

            if best_idx >= 0:
                selected.append(best_idx)
                selected_vecs.append(cand_vecs[best_idx])

        logger.info(
            "PostgresDocumentRepository: MMR rerank completed",
            extra={
                "candidates": len(candidates),
                "selected": len(selected),
                "lambda": lambda_mult,
            },
        )

        return [candidates[i] for i in selected]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity estable (maneja norma cero)."""
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    # ============================================================
    # Nodes (2-tier retrieval)
    # ============================================================
    def save_nodes(
        self,
        document_id: UUID,
        nodes: list[Node],
        *,
        workspace_id: UUID | None = None,
    ) -> None:
        """
        Inserta nodos para un documento (batch insert).

        Sigue el mismo patrón que save_chunks: valida embeddings, verifica
        documento existente, e inserta batch con executemany.
        """
        if not nodes:
            return

        scoped_workspace_id = self._require_workspace_id(workspace_id, "save_nodes")
        self._validate_node_embeddings(nodes)

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                exists = conn.execute(
                    """
                    SELECT 1
                    FROM documents
                    WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL
                    """,
                    (document_id, scoped_workspace_id),
                ).fetchone()

                if not exists:
                    raise DatabaseError(
                        f"Document {document_id} not found for workspace {scoped_workspace_id}"
                    )

                batch = [
                    (
                        node.node_id or uuid4(),
                        scoped_workspace_id,
                        document_id,
                        node.node_index if node.node_index is not None else idx,
                        node.node_text,
                        node.span_start,
                        node.span_end,
                        node.embedding,
                        Json(node.metadata or {}),
                    )
                    for idx, node in enumerate(nodes)
                ]

                with conn.cursor() as cur:
                    try:
                        cur.executemany(
                            """
                            INSERT INTO nodes (
                                id, workspace_id, document_id, node_index,
                                node_text, span_start, span_end, embedding, metadata
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            batch,
                        )
                    except DuplicatePreparedStatement:
                        conn.rollback()
                        for row in batch:
                            conn.execute(
                                """
                                INSERT INTO nodes (
                                    id, workspace_id, document_id, node_index,
                                    node_text, span_start, span_end, embedding, metadata
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                row,
                            )

            logger.info(
                "PostgresDocumentRepository: Saved nodes",
                extra={"document_id": str(document_id), "count": len(nodes)},
            )

        except ValueError:
            raise
        except DatabaseError:
            raise
        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Failed to save nodes",
                extra={"document_id": str(document_id), "error": str(exc)},
            )
            raise DatabaseError(f"Failed to save nodes: {exc}") from exc

    def find_similar_nodes(
        self,
        embedding: list[float],
        top_k: int,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Node]:
        """
        Búsqueda vectorial sobre nodos (cosine distance).

        Sigue el mismo patrón que find_similar_chunks pero consulta la tabla nodes.
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "find_similar_nodes"
        )
        self._validate_embedding(embedding, ctx="Query")

        if top_k <= 0:
            return []

        sql = """
            SELECT
              n.id,
              n.workspace_id,
              n.document_id,
              n.node_index,
              n.node_text,
              n.span_start,
              n.span_end,
              n.embedding,
              n.metadata,
              n.created_at,
              (1 - (n.embedding <=> %s::vector)) as score
            FROM nodes n
            JOIN documents d ON d.id = n.document_id
            WHERE d.deleted_at IS NULL
              AND n.workspace_id = %s
            ORDER BY n.embedding <=> %s::vector
            LIMIT %s
        """

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(
                    sql,
                    (embedding, scoped_workspace_id, embedding, top_k),
                ).fetchall()

            logger.info(
                "PostgresDocumentRepository: Similar nodes retrieved",
                extra={
                    "workspace_id": str(scoped_workspace_id),
                    "count": len(rows),
                    "top_k": top_k,
                },
            )

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Node search failed",
                extra={"workspace_id": str(scoped_workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"Node search failed: {exc}") from exc

        return [
            Node(
                node_id=r[0],
                workspace_id=r[1],
                document_id=r[2],
                node_index=r[3],
                node_text=r[4],
                span_start=r[5],
                span_end=r[6],
                embedding=r[7],
                metadata=r[8] or {},
                created_at=r[9],
                similarity=float(r[10]) if r[10] is not None else None,
            )
            for r in rows
        ]

    def find_chunks_by_node_spans(
        self,
        node_spans: list[tuple[UUID, int, int]],
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """
        Recupera chunks que caen dentro de los spans dados.

        Cada span es (document_id, span_start, span_end) donde span_start/span_end
        son rangos de chunk_index.
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "find_chunks_by_node_spans"
        )

        if not node_spans:
            return []

        # Construir cláusula OR para cada span
        or_clauses = []
        params: list[object] = [scoped_workspace_id]
        for doc_id, span_start, span_end in node_spans:
            or_clauses.append(
                "(c.document_id = %s AND c.chunk_index BETWEEN %s AND %s)"
            )
            params.extend([doc_id, span_start, span_end])

        or_sql = " OR ".join(or_clauses)

        sql = f"""
            SELECT
              c.id,
              c.document_id,
              d.title,
              d.source,
              c.chunk_index,
              c.content,
              c.embedding,
              c.metadata
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.deleted_at IS NULL
              AND d.workspace_id = %s
              AND ({or_sql})
            ORDER BY c.document_id, c.chunk_index
        """

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                rows = conn.execute(sql, tuple(params)).fetchall()

            logger.info(
                "PostgresDocumentRepository: Chunks by node spans retrieved",
                extra={
                    "workspace_id": str(scoped_workspace_id),
                    "spans": len(node_spans),
                    "chunks_found": len(rows),
                },
            )

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Chunks by node spans failed",
                extra={"workspace_id": str(scoped_workspace_id), "error": str(exc)},
            )
            raise DatabaseError(f"Chunks by node spans failed: {exc}") from exc

        return [
            Chunk(
                chunk_id=r[0],
                document_id=r[1],
                document_title=r[2],
                document_source=r[3],
                chunk_index=r[4],
                content=r[5],
                embedding=r[6],
                metadata=r[7] or {},
            )
            for r in rows
        ]

    def delete_nodes_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        """
        Borra nodos de un documento (scoped por workspace vía join).

        Retorna cantidad de filas eliminadas.
        """
        scoped_workspace_id = self._require_workspace_id(
            workspace_id, "delete_nodes_for_document"
        )

        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                result = conn.execute(
                    """
                    DELETE FROM nodes n
                    USING documents d
                    WHERE n.document_id = d.id
                      AND n.document_id = %s
                      AND d.workspace_id = %s
                    """,
                    (document_id, scoped_workspace_id),
                )
            return int(result.rowcount or 0)

        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: Delete nodes failed",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(scoped_workspace_id),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Failed to delete nodes: {exc}") from exc

    # ============================================================
    # Health
    # ============================================================
    def ping(self) -> bool:
        """Chequeo trivial de conectividad."""
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as exc:
            logger.exception(
                "PostgresDocumentRepository: ping failed", extra={"error": str(exc)}
            )
            raise DatabaseError(f"Ping failed: {exc}") from exc
