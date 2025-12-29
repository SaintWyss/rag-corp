import os
from uuid import UUID, uuid4
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Json

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag")


class Store:
    def _conn(self):
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        register_vector(conn)
        return conn

    def upsert_document(self, document_id: UUID, title: str, source: str | None, metadata: dict):
        with self._conn() as conn:
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
        with self._conn() as conn:
            # Preparamos los datos para executemany o loop
            # En este caso simple, loop con execute es suficiente para el MVP
            for idx, (content, emb) in enumerate(zip(chunks, vectors)):
                cid = uuid4()
                conn.execute(
                    """
                    INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cid, document_id, idx, content, emb),
                )

    def search(self, query_vec: list[float], top_k: int = 5):
        # FIX: Agregamos ::vector al placeholder %s para que Postgres sepa castearlo
        with self._conn() as conn:
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

        return [
            {"chunk_id": r[0], "document_id": r[1], "content": r[2], "score": r[3]}
            for r in rows
        ]
