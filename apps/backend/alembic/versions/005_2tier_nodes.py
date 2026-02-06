"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 005_2tier_nodes (Alembic Migration)

Responsibilities:
  - Crear tabla `nodes` para almacenar secciones (agrupaciones de chunks)
    con embeddings vectoriales para retrieval jerárquico 2-tier.
  - Agregar columna `embedding` tipo vector(768) para búsqueda vectorial.
  - Crear índices: document_id, workspace_id, HNSW vectorial,
    y compuesto (document_id, span_start, span_end) para lookups de spans.

Collaborators:
  - PostgreSQL 16+ con pgvector
  - Alembic (framework de migraciones)
  - Tabla documents (FK document_id), Tabla workspaces (FK workspace_id)

Policy:
  - La tabla es independiente: si 2-tier está deshabilitado, queda vacía.
  - HNSW index con m=16 y ef_construction=64 (mismo criterio que chunks).
  - ON DELETE CASCADE en ambas FKs (document/workspace).
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "005_2tier_nodes"
down_revision: Union[str, None] = "004_content_hash_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea tabla nodes + columna embedding + índices para 2-tier retrieval.
    """
    # 1) Tabla nodes (sin embedding aún)
    op.execute("""
        CREATE TABLE nodes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            node_index INTEGER NOT NULL,
            node_text TEXT NOT NULL,
            span_start INTEGER NOT NULL,
            span_end INTEGER NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # 2) Columna embedding vector(768)
    op.execute("ALTER TABLE nodes ADD COLUMN embedding vector(768) NOT NULL")

    # 3) Índices escalares
    op.execute("CREATE INDEX ix_nodes_document_id ON nodes (document_id)")
    op.execute("CREATE INDEX ix_nodes_workspace_id ON nodes (workspace_id)")
    op.execute(
        "CREATE INDEX ix_nodes_document_span "
        "ON nodes (document_id, span_start, span_end)"
    )

    # 4) Índice HNSW para búsqueda vectorial (cosine distance)
    op.execute(
        "CREATE INDEX ix_nodes_embedding_hnsw "
        "ON nodes USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """Elimina tabla nodes y todos sus índices."""
    op.execute("DROP TABLE IF EXISTS nodes CASCADE")
