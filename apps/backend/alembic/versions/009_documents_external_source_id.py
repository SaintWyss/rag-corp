"""
Alembic Migration 009: Add external_source_id to documents
===========================================================
Adds external_source_id column for connector-ingested docs idempotency.
Partial unique index ensures no duplicates per workspace for connector docs
while allowing NULL for manually uploaded documents.
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS external_source_id VARCHAR(500) DEFAULT NULL;
    """
    )
    # Partial unique index: dedup connector docs, allow NULLs for uploads
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_workspace_external_source
        ON documents (workspace_id, external_source_id)
        WHERE external_source_id IS NOT NULL AND deleted_at IS NULL;
    """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS uq_documents_workspace_external_source;
    """
    )
    op.execute(
        """
        ALTER TABLE documents DROP COLUMN IF EXISTS external_source_id;
    """
    )
