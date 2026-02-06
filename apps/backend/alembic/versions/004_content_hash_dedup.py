"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 004_content_hash_dedup (Alembic Migration)

Responsibilities:
  - Agregar columna `content_hash` (VARCHAR(64), nullable) en la tabla
    documents para almacenar el hash SHA-256 del contenido.
  - Crear índice parcial único sobre (workspace_id, content_hash)
    donde content_hash IS NOT NULL, habilitando deduplicación por
    workspace sin afectar documentos existentes (que tienen NULL).

Collaborators:
  - PostgreSQL 16+ (partial unique index)
  - Alembic (framework de migraciones)
  - Tabla documents (workspace_id, content_hash)

Policy:
  - La columna es nullable para backward compatibility:
    documentos existentes sin hash no colisionan.
  - El índice parcial (WHERE content_hash IS NOT NULL) asegura
    que múltiples NULLs coexistan sin violar unicidad.
  - Downgrade elimina el índice y la columna.
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "004_content_hash_dedup"
down_revision: Union[str, None] = "003_fts_tsvector_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ============================================================
# Constants
# ============================================================
_COLUMN_NAME = "content_hash"
_UNIQUE_INDEX = "ix_documents_workspace_content_hash"


def upgrade() -> None:
    """
    Agrega columna content_hash + índice parcial único para dedup.

    Notas:
      - VARCHAR(64): longitud exacta de un hash SHA-256 en hexadecimal.
      - Nullable: documentos existentes quedan con NULL (sin romper nada).
      - Partial unique index: solo aplica cuando content_hash IS NOT NULL,
        permitiendo múltiples NULLs (documentos legacy sin hash).
    """
    # 1) Columna nullable
    op.execute(f"ALTER TABLE documents ADD COLUMN {_COLUMN_NAME} VARCHAR(64)")

    # 2) Índice parcial único (workspace_id, content_hash)
    op.execute(
        f"CREATE UNIQUE INDEX {_UNIQUE_INDEX} "
        f"ON documents (workspace_id, {_COLUMN_NAME}) "
        f"WHERE {_COLUMN_NAME} IS NOT NULL"
    )


def downgrade() -> None:
    """Elimina índice único y columna content_hash."""
    op.execute(f"DROP INDEX IF EXISTS {_UNIQUE_INDEX}")
    op.execute(f"ALTER TABLE documents DROP COLUMN IF EXISTS {_COLUMN_NAME}")
