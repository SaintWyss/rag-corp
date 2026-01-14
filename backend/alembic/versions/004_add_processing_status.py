"""Add PROCESSING to documents status constraint.

Revision ID: 004_add_processing_status
Revises: 003_add_document_file_metadata
Create Date: 2025-01-05

"""

from alembic import op

revision: str = "004_add_processing_status"
down_revision: str | None = "003_add_document_file_metadata"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        "status IS NULL OR status IN ('PENDING', 'PROCESSING', 'READY', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        "status IS NULL OR status IN ('PENDING', 'READY', 'FAILED')",
    )
