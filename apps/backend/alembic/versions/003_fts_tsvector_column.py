"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 003_fts_tsvector_column (Alembic Migration)

Responsibilities:
  - Agregar columna generada `tsv` (tsvector) en la tabla chunks
    para habilitar búsqueda full-text nativa de PostgreSQL.
  - Crear índice GIN sobre la columna tsv para queries eficientes.
  - Idioma: 'spanish' (configurable solo vía nueva migración si se
    necesita cambiar).

Collaborators:
  - PostgreSQL 16+ (GENERATED ALWAYS AS ... STORED)
  - Alembic (framework de migraciones)
  - Tabla chunks.content (fuente del tsvector)

Policy:
  - La columna es GENERATED: se mantiene sincronizada con content
    automáticamente. No requiere cambios en la capa de aplicación
    para writes.
  - Downgrade elimina la columna y el índice.
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "003_fts_tsvector_column"
down_revision: Union[str, None] = "002_hnsw_vector_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ============================================================
# Constants
# ============================================================
_FTS_LANGUAGE = "spanish"
_GIN_INDEX = "ix_chunks_tsv"


def upgrade() -> None:
    """
    Agrega columna tsvector generada + índice GIN para full-text search.

    Notas:
      - GENERATED ALWAYS AS ... STORED: PostgreSQL calcula y persiste el
        tsvector automáticamente en cada INSERT/UPDATE de content.
      - GIN: índice invertido óptimo para tsvector (soporta operador @@).
      - Usamos coalesce para manejar contenido NULL sin error.
    """
    # 1) Columna generada (tsvector)
    op.execute(
        f"ALTER TABLE chunks ADD COLUMN tsv tsvector "
        f"GENERATED ALWAYS AS (to_tsvector('{_FTS_LANGUAGE}', coalesce(content, ''))) STORED"
    )

    # 2) Índice GIN para full-text search
    op.execute(f"CREATE INDEX {_GIN_INDEX} ON chunks USING gin (tsv)")


def downgrade() -> None:
    """Elimina índice GIN y columna tsvector."""
    op.execute(f"DROP INDEX IF EXISTS {_GIN_INDEX}")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS tsv")
