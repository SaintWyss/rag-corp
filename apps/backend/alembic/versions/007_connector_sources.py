"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 007_connector_sources (Alembic Migration)

Responsibilities:
  - Crear tabla connector_sources para almacenar fuentes externas de datos.
  - Índice compuesto (workspace_id, provider) para listados eficientes.
  - CHECK constraint para provider (solo valores válidos del enum).
  - CHECK constraint para status (solo valores válidos).

Collaborators:
  - PostgreSQL 16+ (UUID, JSONB, CHECK)
  - Alembic (framework de migraciones)
  - domain.connectors (ConnectorProvider, ConnectorSourceStatus)
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "007_connector_sources"
down_revision: Union[str, None] = "006_fts_multilang"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ============================================================
# Constants
# ============================================================
_TABLE = "connector_sources"
_ALLOWED_PROVIDERS = ("google_drive",)
_ALLOWED_STATUSES = ("pending", "active", "syncing", "error", "disabled")


def upgrade() -> None:
    """
    Crea la tabla connector_sources con índices y constraints.
    """
    providers_check = ", ".join(f"'{p}'" for p in _ALLOWED_PROVIDERS)
    statuses_check = ", ".join(f"'{s}'" for s in _ALLOWED_STATUSES)

    op.execute(
        f"""
        CREATE TABLE {_TABLE} (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider        VARCHAR(50) NOT NULL,
            folder_id       VARCHAR(500) NOT NULL,
            status          VARCHAR(20) NOT NULL DEFAULT 'pending',
            cursor_json     JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT ck_{_TABLE}_provider CHECK (provider IN ({providers_check})),
            CONSTRAINT ck_{_TABLE}_status CHECK (status IN ({statuses_check}))
        )
    """
    )

    # Índice para listados por workspace + provider
    op.execute(
        f"CREATE INDEX ix_{_TABLE}_workspace_provider "
        f"ON {_TABLE} (workspace_id, provider)"
    )

    # Unique: no duplicar la misma carpeta en el mismo workspace
    op.execute(
        f"CREATE UNIQUE INDEX uq_{_TABLE}_workspace_folder "
        f"ON {_TABLE} (workspace_id, provider, folder_id)"
    )


def downgrade() -> None:
    """Elimina tabla connector_sources y sus índices."""
    op.execute(f"DROP TABLE IF EXISTS {_TABLE} CASCADE")
