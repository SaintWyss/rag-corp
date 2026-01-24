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

LEGACY_WORKSPACE_NAME = "Legacy"
LEGACY_WORKSPACE_BOOTSTRAP_NAME = "Legacy Workspace"
SYSTEM_USER_EMAIL = "system@ragcorp.local"
SYSTEM_USER_PASSWORD_HASH = "disabled"
SYSTEM_USER_ROLE = "admin"


def _has_rows(conn, table_name: str) -> bool:
    row = conn.execute(sa.text(f"SELECT 1 FROM {table_name} LIMIT 1")).fetchone()
    return row is not None


def _create_system_user(conn) -> str:
    # R: Bootstrap-safe owner for fresh installs/legacy DBs with no users.
    system_user_id = str(uuid4())
    conn.execute(
        sa.text(
            """
            INSERT INTO users (id, email, password_hash, role, is_active)
            VALUES (:id, :email, :password_hash, :role, :is_active)
            """
        ),
        {
            "id": system_user_id,
            "email": SYSTEM_USER_EMAIL,
            "password_hash": SYSTEM_USER_PASSWORD_HASH,
            # R: Admin role ensures workspace ownership passes checks; user stays inactive.
            "role": SYSTEM_USER_ROLE,
            "is_active": False,
        },
    )
    return system_user_id


def _select_owner_user_id(conn) -> tuple[str, bool]:
    row = conn.execute(
        sa.text(
            "SELECT id FROM users WHERE role = 'admin' ORDER BY created_at ASC LIMIT 1"
        )
    ).fetchone()
    if row:
        return row[0], False
    row = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if row:
        return row[0], False

    documents_empty = not _has_rows(conn, "documents")
    # R: Avoid blocking fresh installs (no users/documents) or legacy DBs without users.
    return _create_system_user(conn), documents_empty


def _get_or_create_legacy_workspace(conn, owner_user_id: str, name: str) -> str:
    legacy_alias = (
        LEGACY_WORKSPACE_BOOTSTRAP_NAME
        if name == LEGACY_WORKSPACE_NAME
        else LEGACY_WORKSPACE_NAME
    )
    row = conn.execute(
        sa.text(
            "SELECT id FROM workspaces "
            "WHERE owner_user_id = :owner_user_id "
            "AND (name = :name OR name = :legacy_alias) "
            "LIMIT 1"
        ),
        {
            "owner_user_id": owner_user_id,
            "name": name,
            "legacy_alias": legacy_alias,
        },
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
        {"id": legacy_id, "name": name, "owner_user_id": owner_user_id},
    )
    return legacy_id


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    conn = op.get_bind()
    owner_user_id, is_fresh_install = _select_owner_user_id(conn)
    legacy_name = (
        LEGACY_WORKSPACE_BOOTSTRAP_NAME if is_fresh_install else LEGACY_WORKSPACE_NAME
    )
    legacy_workspace_id = _get_or_create_legacy_workspace(
        conn,
        owner_user_id,
        legacy_name,
    )

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
