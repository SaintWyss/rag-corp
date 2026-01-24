"""Add file metadata fields to documents.

Revision ID: 003_add_document_file_metadata
Revises: 002_add_users
Create Date: 2025-01-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_add_document_file_metadata"
down_revision: str | None = "002_add_users"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("file_name", sa.Text, nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.Text, nullable=True))
    op.add_column("documents", sa.Column("storage_key", sa.Text, nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("documents", sa.Column("status", sa.Text, nullable=True))
    op.add_column("documents", sa.Column("error_message", sa.Text, nullable=True))
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        "status IS NULL OR status IN ('PENDING', 'READY', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "status")
    op.drop_column("documents", "uploaded_by_user_id")
    op.drop_column("documents", "storage_key")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "file_name")
