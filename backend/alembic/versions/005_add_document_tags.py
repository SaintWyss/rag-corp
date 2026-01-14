"""Add tags to documents.

Revision ID: 005_add_document_tags
Revises: 004_add_processing_status
Create Date: 2025-01-06

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_add_document_tags"
down_revision: str | None = "004_add_processing_status"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "tags")
