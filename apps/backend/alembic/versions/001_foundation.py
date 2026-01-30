"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: 001_foundation (Alembic Migration)

Responsibilities:
  - Crear el esquema completo de RAG Corp desde cero (migración fundacional).
  - Definir tablas, constraints e índices necesarios para el funcionamiento base.
  - Habilitar extensión pgvector para búsquedas de similitud (embeddings).

Collaborators:
  - PostgreSQL 16+ con extensión pgvector
  - Alembic (framework de migraciones)
  - Capa de repositorios / aplicación (usa este esquema como contrato)

Policy:
  - Esta es una migración BASELINE (fundación). Downgrade NO soportado.
  - Toda evolución futura del esquema debe hacerse con migraciones aditivas (002+).
  - Convención de nombres (constraints / indexes):
      pk_<tabla>                         - Primary keys
      uq_<tabla>_<col>                   - Unique constraints
      ix_<tabla>_<col>                   - Indexes
      fk_<tabla>_<col>__<ref_tabla>      - Foreign keys
  - No modificar este archivo una vez “adoptado” por el equipo.
============================================================
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ============================================================
# Alembic identifiers
# ============================================================
revision: str = "001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea el esquema fundacional completo.

    Orden por carga cognitiva:
      1) Extensiones (pgvector)
      2) Workspaces
      3) Identity (users)
      4) Documents / Storage
      5) Chunks / Embeddings / Retrieval
      6) Logs / Audit
      7) ACL (access control)
    """

    # =========================================================
    # 1) EXTENSIONS
    # =========================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # =========================================================
    # 2) WORKSPACES
    # =========================================================
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "visibility",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'PRIVATE'"),
        ),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workspaces"),
    )

    # Nota: updated_at se actualiza a nivel aplicación (no trigger).
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])
    op.create_index("ix_workspaces_visibility", "workspaces", ["visibility"])
    op.create_index("ix_workspaces_archived_at", "workspaces", ["archived_at"])

    # =========================================================
    # 3) IDENTITY (users)
    # =========================================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column(
            "role", sa.String(50), nullable=False, server_default=sa.text("'employee'")
        ),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # Útil para filtros por rol. (El unique de email ya crea índice implícito.)
    op.create_index("ix_users_role", "users", ["role"])

    # FK diferida: workspaces.owner_user_id -> users.id (ahora que users existe)
    op.create_foreign_key(
        "fk_workspaces_owner_user_id__users",
        "workspaces",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # =========================================================
    # 4) DOCUMENTS / STORAGE
    # =========================================================
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(1000), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
        sa.Column(
            "allowed_roles",
            postgresql.ARRAY(sa.String(50)),
            nullable=True,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
        # Upload / storage
        sa.Column("file_name", sa.String(500), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("storage_key", sa.String(1000), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Estado de procesamiento
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_documents_workspace_id__workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_documents_uploaded_by_user_id__users",
            ondelete="SET NULL",
        ),
    )

    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    # =========================================================
    # 5) CHUNKS / EMBEDDINGS / RETRIEVAL
    # =========================================================
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id__documents",
            ondelete="CASCADE",
        ),
    )

    # pgvector: el tipo `vector(n)` se crea por SQL directo.
    # Dimensión 768: ajustar si cambia el proveedor/embedding model.
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(768)")

    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # Índice ANN opcional (ivfflat). Conviene crear cuando haya datos y se defina estrategia.
    # op.execute(
    #     "CREATE INDEX ix_chunks_embedding_ivfflat "
    #     "ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    # )

    # =========================================================
    # 6) LOGS / AUDIT
    # =========================================================
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )

    op.create_index("ix_audit_events_actor", "audit_events", ["actor"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # =========================================================
    # 7) ACL (Access Control Lists)
    # =========================================================
    op.create_table(
        "workspace_acl",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "access", sa.String(50), nullable=False, server_default=sa.text("'READ'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("workspace_id", "user_id", name="pk_workspace_acl"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_workspace_acl_workspace_id__workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_workspace_acl_user_id__users",
            ondelete="CASCADE",
        ),
    )

    # El PK compuesto ya indexa (workspace_id, user_id). Este índice sí aporta para queries por user_id.
    op.create_index("ix_workspace_acl_user_id", "workspace_acl", ["user_id"])


def downgrade() -> None:
    """
    Downgrade NO soportado para la migración fundacional.

    Política: esta es la base del esquema.
    Para resetear el entorno local: `pnpm stack:reset`.
    """
    raise NotImplementedError(
        "Baseline: downgrade no soportado por política. "
        "Para resetear la base de datos, usar: pnpm stack:reset"
    )
