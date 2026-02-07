"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 010_external_source_metadata (Alembic Migration)

Responsibilities:
  - Agregar campos de metadata externa para detección de cambios en sync.
  - external_source_provider: identifica el proveedor (google_drive, etc.).
  - external_modified_time: timestamp de última modificación en el proveedor.
  - external_etag: fingerprint para detección de cambios (Changes API).
  - external_mime_type: tipo MIME reportado por el proveedor.
  - Permite sync "update-aware": detectar cambios sin re-ingestar todo.

Collaborators:
  - PostgreSQL 16+
  - Alembic (framework de migraciones)
  - Capa de conectores (usa estos campos para idempotencia inteligente)

Policy:
  - Columnas NULLables: compatibilidad con docs existentes.
  - No requiere backfill: campos opcionales que se llenan en sync.
  - Índice parcial existente (009) cubre external_source_id.
============================================================
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Agrega campos de metadata externa para sync update-aware.
    
    Campos:
      - external_source_provider: identifica el proveedor origen (google_drive, etc.)
      - external_modified_time: timestamp de última modificación en el proveedor
      - external_etag: fingerprint/hash para detección de cambios
      - external_mime_type: tipo MIME reportado por el proveedor
    """
    # external_source_provider (si no existe, puede ya existir)
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS external_source_provider VARCHAR(100) DEFAULT NULL;
    """
    )

    # external_modified_time: timestamp con zona horaria
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS external_modified_time TIMESTAMPTZ DEFAULT NULL;
    """
    )

    # external_etag: fingerprint del proveedor
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS external_etag VARCHAR(500) DEFAULT NULL;
    """
    )

    # external_mime_type: tipo MIME reportado por el proveedor
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS external_mime_type VARCHAR(200) DEFAULT NULL;
    """
    )


def downgrade() -> None:
    """
    Remueve campos de metadata externa.
    """
    op.execute(
        """
        ALTER TABLE documents DROP COLUMN IF EXISTS external_mime_type;
    """
    )
    op.execute(
        """
        ALTER TABLE documents DROP COLUMN IF EXISTS external_etag;
    """
    )
    op.execute(
        """
        ALTER TABLE documents DROP COLUMN IF EXISTS external_modified_time;
    """
    )
    op.execute(
        """
        ALTER TABLE documents DROP COLUMN IF EXISTS external_source_provider;
    """
    )
