"""Add workspaces and workspace ACL tables.

Revision ID: 007_add_workspaces_and_acl
Revises: 006_add_audit_events_and_acl
Create Date: 2026-01-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007_add_workspaces_and_acl"
down_revision: Union[str, None] = "006_add_audit_events_and_acl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "visibility",
            sa.Text,
            nullable=False,
            server_default=sa.text("'PRIVATE'"),
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # R: ADR-005 defines uniqueness per owner_user_id + name.
    op.create_unique_constraint(
        "uq_workspaces_owner_user_id_name",
        "workspaces",
        ["owner_user_id", "name"],
    )
    op.create_check_constraint(
        "ck_workspaces_visibility",
        "workspaces",
        "visibility IN ('PRIVATE', 'ORG_READ', 'SHARED')",
    )
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])
    op.create_index("ix_workspaces_visibility", "workspaces", ["visibility"])
    op.create_index("ix_workspaces_archived_at", "workspaces", ["archived_at"])

    op.create_table(
        "workspace_acl",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "access",
            sa.Text,
            nullable=False,
            server_default=sa.text("'READ'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_workspace_acl_workspace_id_user_id",
        "workspace_acl",
        ["workspace_id", "user_id"],
    )
    op.create_check_constraint(
        "ck_workspace_acl_access",
        "workspace_acl",
        "access IN ('READ')",
    )
    op.create_index("ix_workspace_acl_workspace_id", "workspace_acl", ["workspace_id"])
    op.create_index("ix_workspace_acl_user_id", "workspace_acl", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_acl_user_id", table_name="workspace_acl")
    op.drop_index("ix_workspace_acl_workspace_id", table_name="workspace_acl")
    op.drop_constraint(
        "ck_workspace_acl_access", "workspace_acl", type_="check"
    )
    op.drop_constraint(
        "uq_workspace_acl_workspace_id_user_id",
        "workspace_acl",
        type_="unique",
    )
    op.drop_table("workspace_acl")

    op.drop_index("ix_workspaces_archived_at", table_name="workspaces")
    op.drop_index("ix_workspaces_visibility", table_name="workspaces")
    op.drop_index("ix_workspaces_owner_user_id", table_name="workspaces")
    op.drop_constraint(
        "ck_workspaces_visibility", "workspaces", type_="check"
    )
    op.drop_constraint(
        "uq_workspaces_owner_user_id_name", "workspaces", type_="unique"
    )
    op.drop_table("workspaces")
