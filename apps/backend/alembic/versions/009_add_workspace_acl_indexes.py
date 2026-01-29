"""Add workspace ACL indexes for v6 listing performance.

Revision ID: 009_add_workspace_acl_indexes
Revises: 008_docs_workspace_id
Create Date: 2026-01-29
"""

from typing import Sequence, Union

from alembic import op

revision: str = "009_add_workspace_acl_indexes"
down_revision: Union[str, None] = "008_docs_workspace_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Workspace ACL indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workspace_acl_user_id "
        "ON workspace_acl (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workspace_acl_workspace_id "
        "ON workspace_acl (workspace_id)"
    )

    # Workspaces visibility/owner indexes (helpful for single-query listing)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workspaces_visibility "
        "ON workspaces (visibility)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workspaces_owner_user_id "
        "ON workspaces (owner_user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_workspaces_owner_user_id")
    op.execute("DROP INDEX IF EXISTS ix_workspaces_visibility")
    op.execute("DROP INDEX IF EXISTS ix_workspace_acl_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_workspace_acl_user_id")
