"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 002_hnsw_vector_index (Alembic Migration)

Responsibilities:
  - Reemplazar el índice IVFFlat (si existe) por HNSW en la columna
    embedding de la tabla chunks.
  - HNSW ofrece mejor recall sin necesidad de re-training periódico
    (VACUUM/REINDEX) y mejor desempeño con datasets < 1M filas.

Collaborators:
  - PostgreSQL 16+ con pgvector >= 0.5.0
  - Alembic (framework de migraciones)
  - Tabla chunks.embedding vector(768)

Policy:
  - Downgrade recrea el índice IVFFlat anterior (lists=100).
  - IF NOT EXISTS / IF EXISTS para idempotencia en ambientes existentes.
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "002_hnsw_vector_index"
down_revision: Union[str, None] = "001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ============================================================
# Index names
# ============================================================
_OLD_IVFFLAT_INDEX = "chunks_embedding_idx"
_NEW_HNSW_INDEX = "ix_chunks_embedding_hnsw"


def upgrade() -> None:
    """
    Reemplaza IVFFlat por HNSW en chunks.embedding.

    Parámetros HNSW:
      - m = 16: conexiones por nodo (default pgvector). Buen balance
        entre recall y uso de memoria para < 1M filas.
      - ef_construction = 64: calidad de construcción del grafo.
        Más alto = mejor recall pero build más lento. 64 es el default
        de pgvector y adecuado para el volumen esperado.

    Nota: No usamos CONCURRENTLY aquí porque Alembic corre dentro de
    una transacción. Para tablas muy grandes en producción, ejecutar
    manualmente con CONCURRENTLY fuera de Alembic.
    """
    # 1) Eliminar índice IVFFlat previo (puede existir por setup manual
    #    o por init.sql histórico).
    op.execute(f"DROP INDEX IF EXISTS {_OLD_IVFFLAT_INDEX}")

    # 2) Eliminar HNSW previo (idempotencia en caso de re-run).
    op.execute(f"DROP INDEX IF EXISTS {_NEW_HNSW_INDEX}")

    # 3) Crear índice HNSW.
    op.execute(
        f"CREATE INDEX {_NEW_HNSW_INDEX} "
        "ON chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """
    Rollback: elimina HNSW y recrea IVFFlat (lists=100).
    """
    op.execute(f"DROP INDEX IF EXISTS {_NEW_HNSW_INDEX}")
    op.execute(
        f"CREATE INDEX {_OLD_IVFFLAT_INDEX} "
        "ON chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
