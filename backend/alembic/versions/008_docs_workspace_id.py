"""Scope documents to workspaces with legacy backfill.

Revision ID: 008_docs_workspace_id
Revises: 007_add_workspaces_and_acl
Create Date: 2026-01-21

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_docs_workspace_id"
down_revision: Union[str, None] = "007_add_workspaces_and_acl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _select_owner_user_id(conn) -> str:
    row = conn.execute(
        sa.text(
            "SELECT id FROM users WHERE role = 'admin' ORDER BY created_at ASC LIMIT 1"
        )
    ).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if row:
        return row[0]
    raise RuntimeError(
        "No users found for legacy workspace ownership. "
        "Create an admin with backend/scripts/create_admin.py before migrating."
    )


def _get_or_create_legacy_workspace(conn, owner_user_id: str) -> str:
    row = conn.execute(
        sa.text(
            "SELECT id FROM workspaces "
            "WHERE owner_user_id = :owner_user_id AND name = :name "
            "LIMIT 1"
        ),
        {"owner_user_id": owner_user_id, "name": "Legacy"},
    ).fetchone()
    if row:
        return row[0]

    legacy_id = str(uuid4())
    conn.execute(
        sa.text(
            """
            INSERT INTO workspaces (
                id,
                name,
                visibility,
                owner_user_id,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :name,
                'PRIVATE',
                :owner_user_id,
                now(),
                now()
            )
            """
        ),
        {"id": legacy_id, "name": "Legacy", "owner_user_id": owner_user_id},
    )
    return legacy_id


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    conn = op.get_bind()
    owner_user_id = _select_owner_user_id(conn)
    legacy_workspace_id = _get_or_create_legacy_workspace(conn, owner_user_id)

    conn.execute(
        sa.text(
            "UPDATE documents SET workspace_id = :workspace_id "
            "WHERE workspace_id IS NULL"
        ),
        {"workspace_id": legacy_workspace_id},
    )

    op.alter_column(
        "documents",
        "workspace_id",
        nullable=False,
        server_default=sa.text(f"'{legacy_workspace_id}'::uuid"),
    )
    op.create_foreign_key(
        "fk_documents_workspace_id",
        "documents",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_workspace_id", table_name="documents")
    op.drop_constraint("fk_documents_workspace_id", "documents", type_="foreignkey")
    op.drop_column("documents", "workspace_id")
