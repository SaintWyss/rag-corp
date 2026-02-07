"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 008_connector_accounts (Alembic Migration)

Responsibilities:
  - Crear tabla connector_accounts para almacenar cuentas OAuth vinculadas.
  - Unique constraint por (workspace_id, provider): una cuenta por conector por workspace.
  - Almacena refresh_token cifrado (Fernet), nunca en claro.

Collaborators:
  - PostgreSQL 16+ (UUID, TEXT, TIMESTAMPTZ)
  - Alembic (framework de migraciones)
  - domain.connectors (ConnectorAccount)
============================================================
"""

from typing import Sequence, Union

from alembic import op

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "008_connector_accounts"
down_revision: Union[str, None] = "007_connector_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ============================================================
# Constants
# ============================================================
_TABLE = "connector_accounts"
_ALLOWED_PROVIDERS = ("google_drive",)


def upgrade() -> None:
    """Crea tabla connector_accounts con unique constraint."""
    providers_check = ", ".join(f"'{p}'" for p in _ALLOWED_PROVIDERS)

    op.execute(
        f"""
        CREATE TABLE {_TABLE} (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider                VARCHAR(50) NOT NULL,
            account_email           VARCHAR(320) NOT NULL,
            encrypted_refresh_token TEXT NOT NULL,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT ck_{_TABLE}_provider CHECK (provider IN ({providers_check}))
        )
    """
    )

    # Una cuenta por provider por workspace
    op.execute(
        f"CREATE UNIQUE INDEX uq_{_TABLE}_workspace_provider "
        f"ON {_TABLE} (workspace_id, provider)"
    )


def downgrade() -> None:
    """Elimina tabla connector_accounts."""
    op.execute(f"DROP TABLE IF EXISTS {_TABLE} CASCADE")
