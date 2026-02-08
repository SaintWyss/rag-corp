"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 011_workspace_acl_roles (Alembic Migration)

Responsibilities:
  - Agregar columna `role` a tabla workspace_acl (VIEWER | EDITOR).
  - Agregar columna `granted_by` (UUID nullable) para auditoría.
  - CHECK CONSTRAINT sobre valores válidos de role.
  - Migrar datos existentes: filas con access='READ' → role='VIEWER'.

Collaborators:
  - PostgreSQL 16+
  - Alembic (framework de migraciones)
  - workspace_acl table (ya existente)

Policy:
  - Backward compatible: columna `access` se mantiene.
  - Default 'VIEWER' para datos existentes y nuevos.
  - Downgrade limpia las columnas nuevas.
============================================================
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Agrega role y granted_by a workspace_acl."""
    # 1. Columna role con default para datos existentes
    op.execute(
        """
        ALTER TABLE workspace_acl
        ADD COLUMN IF NOT EXISTS role VARCHAR(10) NOT NULL DEFAULT 'VIEWER';
    """
    )

    # 2. CHECK CONSTRAINT para valores válidos
    op.execute(
        """
        ALTER TABLE workspace_acl
        ADD CONSTRAINT ck_workspace_acl_role
        CHECK (role IN ('VIEWER', 'EDITOR'));
    """
    )

    # 3. Columna granted_by (nullable, auditoría)
    op.execute(
        """
        ALTER TABLE workspace_acl
        ADD COLUMN IF NOT EXISTS granted_by UUID DEFAULT NULL;
    """
    )


def downgrade() -> None:
    """Remueve role y granted_by de workspace_acl."""
    op.execute(
        "ALTER TABLE workspace_acl DROP CONSTRAINT IF EXISTS ck_workspace_acl_role;"
    )
    op.execute("ALTER TABLE workspace_acl DROP COLUMN IF EXISTS granted_by;")
    op.execute("ALTER TABLE workspace_acl DROP COLUMN IF EXISTS role;")
