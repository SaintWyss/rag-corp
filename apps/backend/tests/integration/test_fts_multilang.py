"""
Name: FTS Multi-language Integration Tests

Responsibilities:
  - Test per-workspace FTS language configuration with real PostgreSQL
  - Verify tsv column is computed correctly for each language
  - Verify FTS queries use the correct regconfig per workspace
  - Test cross-workspace language isolation

Collaborators:
  - PostgresDocumentRepository: Repository under test
  - PostgreSQL + tsvector: Full-text search under test
  - pytest: Test framework

Notes:
  - Requires running PostgreSQL instance (use Docker Compose)
  - Mark with @pytest.mark.integration
  - Skipped unless RUN_INTEGRATION=1
"""

import os

import pytest

# Skip BEFORE importing app.* to avoid triggering env validation during collection
if os.getenv("RUN_INTEGRATION") != "1":
    pytest.skip(
        "Set RUN_INTEGRATION=1 to run integration tests", allow_module_level=True
    )

from uuid import uuid4

import psycopg
from app.infrastructure.repositories.postgres.document import PostgresDocumentRepository

pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag"
)


# ============================================================================
# Helpers
# ============================================================================


def _insert_user(conn: psycopg.Connection, user_id, email: str) -> None:
    conn.execute(
        """
        INSERT INTO users (id, email, password_hash, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, email, "test-hash", "admin", True),
    )


def _insert_workspace(
    conn: psycopg.Connection,
    workspace_id,
    owner_user_id,
    name: str,
    fts_language: str = "spanish",
) -> None:
    conn.execute(
        """
        INSERT INTO workspaces (
            id, name, description, visibility, owner_user_id,
            archived_at, fts_language, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, NULL, %s, NOW(), NOW())
        """,
        (workspace_id, name, None, "PRIVATE", owner_user_id, fts_language),
    )


def _insert_document(
    conn: psycopg.Connection,
    doc_id,
    workspace_id,
    title: str = "Test Doc",
) -> None:
    conn.execute(
        """
        INSERT INTO documents (id, workspace_id, title, status)
        VALUES (%s, %s, %s, 'ready')
        """,
        (doc_id, workspace_id, title),
    )


def _insert_chunk_with_tsv(
    conn: psycopg.Connection,
    chunk_id,
    doc_id,
    content: str,
    fts_language: str,
    chunk_index: int = 0,
) -> None:
    """Insert a chunk with tsv computed for the given language."""
    embedding = [0.1] * 768
    conn.execute(
        """
        INSERT INTO chunks (id, document_id, chunk_index, content, embedding, tsv)
        VALUES (%s, %s, %s, %s, %s::vector, to_tsvector(%s::regconfig, coalesce(%s, '')))
        """,
        (chunk_id, doc_id, chunk_index, content, str(embedding), fts_language, content),
    )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def db_repository():
    return PostgresDocumentRepository()


@pytest.fixture(scope="module")
def fts_context(db_conn):
    """Create two workspaces: one spanish, one english, with test data."""
    owner_id = uuid4()
    ws_spanish = uuid4()
    ws_english = uuid4()
    doc_spanish = uuid4()
    doc_english = uuid4()
    chunk_spanish = uuid4()
    chunk_english = uuid4()

    email = f"fts-owner-{owner_id}@example.com"
    _insert_user(db_conn, owner_id, email)

    _insert_workspace(
        db_conn, ws_spanish, owner_id, "FTS Spanish WS", fts_language="spanish"
    )
    _insert_workspace(
        db_conn, ws_english, owner_id, "FTS English WS", fts_language="english"
    )

    _insert_document(db_conn, doc_spanish, ws_spanish, "Doc Spanish")
    _insert_document(db_conn, doc_english, ws_english, "Doc English")

    # Spanish content: "Los algoritmos de inteligencia artificial procesan datos"
    _insert_chunk_with_tsv(
        db_conn,
        chunk_spanish,
        doc_spanish,
        "Los algoritmos de inteligencia artificial procesan datos complejos",
        fts_language="spanish",
    )

    # English content: "Machine learning algorithms process complex data"
    _insert_chunk_with_tsv(
        db_conn,
        chunk_english,
        doc_english,
        "Machine learning algorithms process complex data efficiently",
        fts_language="english",
    )

    yield {
        "owner_id": owner_id,
        "ws_spanish": ws_spanish,
        "ws_english": ws_english,
        "doc_spanish": doc_spanish,
        "doc_english": doc_english,
        "chunk_spanish": chunk_spanish,
        "chunk_english": chunk_english,
    }

    # Cleanup (chunks cascade from documents)
    db_conn.execute("DELETE FROM documents WHERE id = %s", (doc_spanish,))
    db_conn.execute("DELETE FROM documents WHERE id = %s", (doc_english,))
    db_conn.execute("DELETE FROM workspaces WHERE id = %s", (ws_spanish,))
    db_conn.execute("DELETE FROM workspaces WHERE id = %s", (ws_english,))
    db_conn.execute("DELETE FROM users WHERE id = %s", (owner_id,))


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.integration
class TestFtsMultilang:
    def test_fts_spanish_workspace_finds_spanish_content(
        self, db_repository, fts_context
    ):
        """R: Spanish workspace with spanish FTS finds spanish content."""
        results = db_repository.find_chunks_full_text(
            query_text="algoritmos inteligencia artificial",
            top_k=5,
            workspace_id=fts_context["ws_spanish"],
            fts_language="spanish",
        )

        assert len(results) >= 1
        assert any("algoritmos" in c.content for c in results), (
            "Expected spanish chunk in results"
        )

    def test_fts_english_workspace_finds_english_content(
        self, db_repository, fts_context
    ):
        """R: English workspace with english FTS finds english content."""
        results = db_repository.find_chunks_full_text(
            query_text="machine learning algorithms",
            top_k=5,
            workspace_id=fts_context["ws_english"],
            fts_language="english",
        )

        assert len(results) >= 1
        assert any("algorithms" in c.content for c in results), (
            "Expected english chunk in results"
        )

    def test_fts_cross_language_isolation(self, db_repository, fts_context):
        """R: Each workspace only finds content indexed in its own language."""
        # Spanish query on english workspace should find nothing
        results_wrong_ws = db_repository.find_chunks_full_text(
            query_text="algoritmos inteligencia artificial",
            top_k=5,
            workspace_id=fts_context["ws_english"],
            fts_language="english",
        )

        # Workspace isolation: english workspace has no spanish content
        spanish_in_english = [c for c in results_wrong_ws if "algoritmos" in c.content]
        assert len(spanish_in_english) == 0, (
            "Spanish content should not appear in english workspace"
        )

        # English query on spanish workspace should find nothing
        results_wrong_ws2 = db_repository.find_chunks_full_text(
            query_text="machine learning algorithms",
            top_k=5,
            workspace_id=fts_context["ws_spanish"],
            fts_language="spanish",
        )

        english_in_spanish = [c for c in results_wrong_ws2 if "algorithms" in c.content]
        assert len(english_in_spanish) == 0, (
            "English content should not appear in spanish workspace"
        )
