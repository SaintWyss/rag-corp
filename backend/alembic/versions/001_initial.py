"""Initial schema with pgvector

Revision ID: 001_initial
Revises:
Create Date: 2025-01-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_filename", "documents", ["filename"])

    # Create chunks table with vector column
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("embedding", sa.LargeBinary, nullable=True),  # Will store vector
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # Add vector column (using raw SQL for pgvector type)
    op.execute(
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(768)"
    )

    # Create HNSW index for similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding_vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding_hnsw", "chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_filename", "documents")
    op.drop_table("documents")
    op.execute("DROP EXTENSION IF EXISTS vector")
