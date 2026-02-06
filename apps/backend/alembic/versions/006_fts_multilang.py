"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 006_fts_multilang (Alembic Migration)

Responsibilities:
  - Agregar columna `fts_language` a workspaces (per-workspace FTS language).
  - Convertir columna GENERATED `tsv` en chunks a columna regular (para
    soportar idioma variable por workspace).
  - Backfill tsv existente con 'spanish' (default).
  - Recrear índice GIN sobre tsv.

Collaborators:
  - PostgreSQL 16+ (regconfig, tsvector, GIN)
  - Alembic (framework de migraciones)
  - Tabla workspaces (nueva columna fts_language)
  - Tabla chunks (columna tsv convertida de GENERATED a regular)

Policy:
  - Allowlist estricta via CHECK constraint en DB.
  - Backfill garantiza que chunks existentes mantienen tsv válido.
  - Downgrade revierte a columna GENERATED con 'spanish'.
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "006_fts_multilang"
down_revision: Union[str, None] = "005_2tier_nodes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ============================================================
# Constants
# ============================================================
_FTS_DEFAULT_LANGUAGE = "spanish"
_FTS_ALLOWED_LANGUAGES = ("spanish", "english", "simple")
_GIN_INDEX = "ix_chunks_tsv"
_CHECK_CONSTRAINT = "ck_workspaces_fts_language"


def upgrade() -> None:
    """
    Agrega soporte multi-idioma para FTS:
      1) Columna fts_language en workspaces (con CHECK constraint).
      2) Convierte tsv de GENERATED a regular + backfill + GIN.
    """
    # 1) Agregar fts_language a workspaces
    allowed = ", ".join(f"'{lang}'" for lang in _FTS_ALLOWED_LANGUAGES)
    op.execute(
        f"ALTER TABLE workspaces "
        f"ADD COLUMN fts_language VARCHAR(20) NOT NULL DEFAULT '{_FTS_DEFAULT_LANGUAGE}'"
    )
    op.execute(
        f"ALTER TABLE workspaces "
        f"ADD CONSTRAINT {_CHECK_CONSTRAINT} "
        f"CHECK (fts_language IN ({allowed}))"
    )

    # 2) Drop GIN index (depends on tsv column)
    op.execute(f"DROP INDEX IF EXISTS {_GIN_INDEX}")

    # 3) Drop GENERATED tsv column
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS tsv")

    # 4) Recreate tsv as regular column
    op.execute("ALTER TABLE chunks ADD COLUMN tsv tsvector")

    # 5) Backfill existing chunks with default language
    op.execute(
        f"UPDATE chunks SET tsv = to_tsvector("
        f"'{_FTS_DEFAULT_LANGUAGE}'::regconfig, coalesce(content, ''))"
    )

    # 6) Set NOT NULL after backfill
    op.execute("ALTER TABLE chunks ALTER COLUMN tsv SET NOT NULL")

    # 7) Recreate GIN index
    op.execute(f"CREATE INDEX {_GIN_INDEX} ON chunks USING gin (tsv)")


def downgrade() -> None:
    """Revierte a columna GENERATED con idioma fijo 'spanish'."""
    # 1) Drop constraint + column from workspaces
    op.execute(f"ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS {_CHECK_CONSTRAINT}")
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS fts_language")

    # 2) Drop GIN index + regular tsv column
    op.execute(f"DROP INDEX IF EXISTS {_GIN_INDEX}")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS tsv")

    # 3) Recreate tsv as GENERATED column (original migration 003 behavior)
    op.execute(
        f"ALTER TABLE chunks ADD COLUMN tsv tsvector "
        f"GENERATED ALWAYS AS (to_tsvector('{_FTS_DEFAULT_LANGUAGE}', "
        f"coalesce(content, ''))) STORED"
    )

    # 4) Recreate GIN index
    op.execute(f"CREATE INDEX {_GIN_INDEX} ON chunks USING gin (tsv)")
