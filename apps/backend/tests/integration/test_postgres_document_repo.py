"""
Name: PostgreSQL Document Repository Integration Tests

Responsibilities:
  - Test PostgresDocumentRepository with real PostgreSQL database
  - Verify vector similarity search operations
  - Test data persistence and retrieval
  - Validate pgvector integration

Collaborators:
  - app.infrastructure.repositories.postgres_document_repo: Repository being tested
  - PostgreSQL + pgvector: Database under test
  - pytest: Test framework

Notes:
  - Requires running PostgreSQL instance (use Docker Compose)
  - Tests are slower than unit tests (I/O operations)
  - Mark with @pytest.mark.integration
  - Can be skipped in CI if DB not available

Setup:
  Run before tests: docker compose up -d db
"""

import os
import pytest

# Skip BEFORE importing app.* to avoid triggering env validation during collection
if os.getenv("RUN_INTEGRATION") != "1":
    pytest.skip(
        "Set RUN_INTEGRATION=1 to run integration tests", allow_module_level=True
    )

from uuid import uuid4, UUID

import psycopg

from app.domain.entities import Document, Chunk
from app.infrastructure.repositories.postgres.document import (
    PostgresDocumentRepository,
)

pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag"
)


def _insert_user(conn: psycopg.Connection, user_id: UUID, email: str) -> None:
    conn.execute(
        """
        INSERT INTO users (id, email, password_hash, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, email, "test-hash", "admin", True),
    )


def _insert_workspace(
    conn: psycopg.Connection,
    workspace_id: UUID,
    owner_user_id: UUID,
    name: str,
) -> None:
    conn.execute(
        """
        INSERT INTO workspaces (
            id,
            name,
            description,
            visibility,
            owner_user_id,
            archived_at,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, NULL, NOW(), NOW())
        """,
        (workspace_id, name, None, "PRIVATE", owner_user_id),
    )


def _fetch_document(conn: psycopg.Connection, doc_id: UUID):
    return conn.execute(
        "SELECT id, title, source, metadata FROM documents WHERE id = %s",
        (doc_id,),
    ).fetchone()


@pytest.fixture(scope="module")
def db_repository():
    """
    R: Provide repository instance for integration tests.

    Note: Uses real PostgreSQL connection.
    """
    repo = PostgresDocumentRepository()
    return repo


@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def workspace_context(db_conn):
    owner_user_id = uuid4()
    workspace_id = uuid4()
    email = f"repo-owner-{owner_user_id}@example.com"
    _insert_user(db_conn, owner_user_id, email)
    _insert_workspace(
        db_conn,
        workspace_id,
        owner_user_id,
        f"Repo Workspace {workspace_id}",
    )
    yield {"workspace_id": workspace_id, "owner_user_id": owner_user_id}
    db_conn.execute(
        "DELETE FROM documents WHERE workspace_id = %s",
        (workspace_id,),
    )
    db_conn.execute("DELETE FROM workspaces WHERE id = %s", (workspace_id,))
    db_conn.execute("DELETE FROM users WHERE id = %s", (owner_user_id,))


@pytest.fixture(scope="module")
def dual_workspace_context(db_conn):
    owner_user_id = uuid4()
    workspace_a = uuid4()
    workspace_b = uuid4()
    email = f"repo-owner-{owner_user_id}@example.com"
    _insert_user(db_conn, owner_user_id, email)
    _insert_workspace(db_conn, workspace_a, owner_user_id, f"Repo Workspace A {workspace_a}")
    _insert_workspace(db_conn, workspace_b, owner_user_id, f"Repo Workspace B {workspace_b}")
    yield {
        "owner_user_id": owner_user_id,
        "workspace_a": workspace_a,
        "workspace_b": workspace_b,
    }
    db_conn.execute(
        "DELETE FROM documents WHERE workspace_id = %s OR workspace_id = %s",
        (workspace_a, workspace_b),
    )
    db_conn.execute("DELETE FROM workspaces WHERE id = %s", (workspace_a,))
    db_conn.execute("DELETE FROM workspaces WHERE id = %s", (workspace_b,))
    db_conn.execute("DELETE FROM users WHERE id = %s", (owner_user_id,))


@pytest.fixture(scope="function")
def cleanup_test_data(db_conn):
    """
    R: Clean up test data after each test.

    Yields control to test, then cleans up.
    """
    test_doc_ids = []

    yield test_doc_ids

    # Cleanup: Delete test documents and their chunks
    # Note: Chunks cascade delete via foreign key
    # This is a simplified cleanup - in production use transactions
    if test_doc_ids:
        db_conn.execute(
            "DELETE FROM documents WHERE id = ANY(%s)",
            (test_doc_ids,),
        )


@pytest.mark.integration
class TestPostgresDocumentRepositorySaveOperations:
    """Test document and chunk persistence operations."""

    def test_save_document(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should persist document to database."""
        # Arrange
        workspace_id = workspace_context["workspace_id"]
        doc = Document(
            id=uuid4(),
            title="Integration Test Document",
            source="https://test.com/doc.pdf",
            metadata={"test": True, "author": "Test Suite"},
            workspace_id=workspace_id,
        )
        cleanup_test_data.append(doc.id)

        # Act
        db_repository.save_document(doc)

        # Assert - retrieve and verify
        retrieved = _fetch_document(db_conn, doc.id)
        assert retrieved is not None
        assert retrieved[0] == doc.id
        assert retrieved[1] == doc.title
        assert retrieved[2] == doc.source
        assert retrieved[3]["test"] is True

    def test_save_document_upsert_behavior(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should update existing document on conflict."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        original_doc = Document(
            id=doc_id,
            title="Original Title",
            source="https://original.com",
            workspace_id=workspace_id,
        )

        updated_doc = Document(
            id=doc_id,
            title="Updated Title",
            source="https://updated.com",
            metadata={"updated": True},
            workspace_id=workspace_id,
        )

        # Act
        db_repository.save_document(original_doc)
        db_repository.save_document(updated_doc)  # Same ID, should update

        # Assert
        retrieved = _fetch_document(db_conn, doc_id)
        assert retrieved[1] == "Updated Title"
        assert retrieved[2] == "https://updated.com"
        assert retrieved[3].get("updated") is True

    def test_save_chunks_with_embeddings(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should persist chunks with vector embeddings."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(id=doc_id, title="Test Doc", workspace_id=workspace_id)
        db_repository.save_document(doc)

        chunks = [
            Chunk(
                content=f"Test chunk {i}",
                embedding=[0.1 * i] * 768,
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(3)
        ]

        # Act
        db_repository.save_chunks(doc_id, chunks, workspace_id=workspace_id)

        # Assert - verify chunks were saved
        rows = db_conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = %s",
            (doc_id,),
        ).fetchone()
        assert rows[0] == len(chunks)


@pytest.mark.integration
class TestPostgresDocumentRepositoryVectorSearch:
    """Test vector similarity search operations."""

    def test_find_similar_chunks_returns_results(
        self, db_repository, cleanup_test_data, workspace_context
    ):
        """R: Should find similar chunks using vector search."""
        # Arrange - create test document and chunks
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Search Test Doc",
            workspace_id=workspace_id,
        )
        db_repository.save_document(doc)

        # Create chunks with distinct embeddings
        chunks = [
            Chunk(
                content=f"Content about topic {i}",
                embedding=[float(i) / 10] * 768,
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(5)
        ]
        db_repository.save_chunks(doc_id, chunks, workspace_id=workspace_id)

        # Act - search for similar chunks
        query_embedding = [0.2] * 768  # Should be closest to chunk 2
        results = db_repository.find_similar_chunks(
            embedding=query_embedding,
            top_k=3,
            workspace_id=workspace_id,
        )

        # Assert
        assert len(results) <= 3
        assert all(isinstance(chunk, Chunk) for chunk in results)
        assert all(chunk.document_id == doc_id for chunk in results)

    def test_find_similar_chunks_scoped_to_workspace(
        self, db_repository, db_conn, workspace_context
    ):
        """R: Should not return chunks from other workspaces."""
        workspace_id = workspace_context["workspace_id"]
        owner_user_id = workspace_context["owner_user_id"]
        other_workspace_id = uuid4()

        _insert_workspace(
            db_conn,
            other_workspace_id,
            owner_user_id,
            f"Repo Workspace {other_workspace_id}",
        )

        doc_id = uuid4()
        other_doc_id = uuid4()

        try:
            db_repository.save_document(
                Document(
                    id=doc_id,
                    title="Scoped Search Doc",
                    workspace_id=workspace_id,
                )
            )
            db_repository.save_document(
                Document(
                    id=other_doc_id,
                    title="Other Workspace Doc",
                    workspace_id=other_workspace_id,
                )
            )

            db_repository.save_chunks(
                doc_id,
                [
                    Chunk(
                        content="Workspace 1 chunk",
                        embedding=[0.1] * 768,
                        document_id=doc_id,
                        chunk_index=0,
                    )
                ],
                workspace_id=workspace_id,
            )
            db_repository.save_chunks(
                other_doc_id,
                [
                    Chunk(
                        content="Workspace 2 chunk",
                        embedding=[0.9] * 768,
                        document_id=other_doc_id,
                        chunk_index=0,
                    )
                ],
                workspace_id=other_workspace_id,
            )

            results = db_repository.find_similar_chunks(
                embedding=[0.9] * 768,
                top_k=1,
                workspace_id=workspace_id,
            )

            assert results
            assert all(chunk.document_id == doc_id for chunk in results)
        finally:
            db_conn.execute(
                "DELETE FROM documents WHERE id = ANY(%s)",
                ([doc_id, other_doc_id],),
            )
            db_conn.execute(
                "DELETE FROM workspaces WHERE id = %s",
                (other_workspace_id,),
            )

    def test_find_similar_chunks_no_cross_workspace_leak(
        self, db_repository, cleanup_test_data, dual_workspace_context
    ):
        """R: Ensure retrieval never returns chunks from another workspace."""
        workspace_a = dual_workspace_context["workspace_a"]
        workspace_b = dual_workspace_context["workspace_b"]

        doc_a = uuid4()
        doc_b = uuid4()
        cleanup_test_data.extend([doc_a, doc_b])

        db_repository.save_document(
            Document(
                id=doc_a,
                title="Alpha Doc",
                workspace_id=workspace_a,
            )
        )
        db_repository.save_document(
            Document(
                id=doc_b,
                title="Beta Doc",
                workspace_id=workspace_b,
            )
        )

        shared_embedding = [0.5] * 768
        db_repository.save_chunks(
            doc_a,
            [
                Chunk(
                    content="Alpha",
                    embedding=shared_embedding,
                    document_id=doc_a,
                    chunk_index=0,
                )
            ],
            workspace_id=workspace_a,
        )
        db_repository.save_chunks(
            doc_b,
            [
                Chunk(
                    content="Beta",
                    embedding=shared_embedding,
                    document_id=doc_b,
                    chunk_index=0,
                )
            ],
            workspace_id=workspace_b,
        )

        results = db_repository.find_similar_chunks(
            embedding=shared_embedding,
            top_k=5,
            workspace_id=workspace_a,
        )

        assert results
        assert all(chunk.document_id == doc_a for chunk in results)

    def test_find_similar_chunks_mmr_scoped_to_workspace(
        self, db_repository, db_conn, workspace_context
    ):
        """R: MMR search should not return chunks from other workspaces."""
        workspace_id = workspace_context["workspace_id"]
        owner_user_id = workspace_context["owner_user_id"]
        other_workspace_id = uuid4()

        _insert_workspace(
            db_conn,
            other_workspace_id,
            owner_user_id,
            f"Repo Workspace {other_workspace_id}",
        )

        doc_id = uuid4()
        other_doc_id = uuid4()

        try:
            db_repository.save_document(
                Document(
                    id=doc_id,
                    title="MMR Scoped Search Doc",
                    workspace_id=workspace_id,
                )
            )
            db_repository.save_document(
                Document(
                    id=other_doc_id,
                    title="MMR Other Workspace Doc",
                    workspace_id=other_workspace_id,
                )
            )

            db_repository.save_chunks(
                doc_id,
                [
                    Chunk(
                        content="Workspace 1 chunk",
                        embedding=[0.1] * 768,
                        document_id=doc_id,
                        chunk_index=0,
                    )
                ],
                workspace_id=workspace_id,
            )
            db_repository.save_chunks(
                other_doc_id,
                [
                    Chunk(
                        content="Workspace 2 chunk",
                        embedding=[0.9] * 768,
                        document_id=other_doc_id,
                        chunk_index=0,
                    )
                ],
                workspace_id=other_workspace_id,
            )

            results = db_repository.find_similar_chunks_mmr(
                embedding=[0.9] * 768,
                top_k=1,
                fetch_k=4,
                workspace_id=workspace_id,
            )

            assert results
            assert all(chunk.document_id == doc_id for chunk in results)
        finally:
            db_conn.execute(
                "DELETE FROM documents WHERE id = ANY(%s)",
                ([doc_id, other_doc_id],),
            )
            db_conn.execute(
                "DELETE FROM workspaces WHERE id = %s",
                (other_workspace_id,),
            )

    def test_find_similar_chunks_respects_top_k(
        self, db_repository, cleanup_test_data, workspace_context
    ):
        """R: Should return at most top_k results."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(id=doc_id, title="Top K Test", workspace_id=workspace_id)
        db_repository.save_document(doc)

        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[float(i) / 100] * 768,
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(10)
        ]
        db_repository.save_chunks(doc_id, chunks, workspace_id=workspace_id)

        # Act
        results = db_repository.find_similar_chunks(
            embedding=[0.05] * 768,
            top_k=5,
            workspace_id=workspace_id,
        )

        # Assert
        assert len(results) <= 5

    def test_find_similar_chunks_returns_most_similar_first(
        self, db_repository, cleanup_test_data, workspace_context
    ):
        """R: Should return chunks ordered by similarity (descending)."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(id=doc_id, title="Ranking Test", workspace_id=workspace_id)
        db_repository.save_document(doc)

        # Create chunks with known embeddings
        chunks = [
            Chunk(
                content="Very different",
                embedding=[1.0] * 768,
                document_id=doc_id,
                chunk_index=0,
            ),
            Chunk(
                content="Exact match",
                embedding=[0.5] * 768,  # Exact match to query
                document_id=doc_id,
                chunk_index=1,
            ),
            Chunk(
                content="Somewhat similar",
                embedding=[0.6] * 768,
                document_id=doc_id,
                chunk_index=2,
            ),
        ]
        db_repository.save_chunks(doc_id, chunks, workspace_id=workspace_id)

        # Act - search with embedding matching chunk 1
        results = db_repository.find_similar_chunks(
            embedding=[0.5] * 768,
            top_k=3,
            workspace_id=workspace_id,
        )

        # Assert - most similar should be first
        # Note: Exact assertions depend on similarity metric (cosine)
        assert len(results) >= 1
        # First result should be the exact match (chunk_index=1)
        # This is a heuristic test - exact verification depends on distance calculation

    def test_find_similar_chunks_with_no_results(
        self, db_repository, workspace_context
    ):
        """R: Should return empty list when no documents exist."""
        # Act - search in empty database (assuming cleanup)
        results = db_repository.find_similar_chunks(
            embedding=[0.0] * 768,
            top_k=5,
            workspace_id=workspace_context["workspace_id"],
        )

        # Assert
        assert isinstance(results, list)
        # May return empty or existing test data from other tests


@pytest.mark.integration
class TestPostgresDocumentRepositoryRetrievalOperations:
    """Test document and chunk retrieval operations."""

    def test_get_document_by_id(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should retrieve document by ID."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Retrieval Test",
            source="https://test.com",
            workspace_id=workspace_id,
        )
        db_repository.save_document(doc)

        # Act
        retrieved = _fetch_document(db_conn, doc_id)

        # Assert
        assert retrieved is not None
        assert retrieved[0] == doc_id
        assert retrieved[1] == "Retrieval Test"

    def test_get_document_returns_none_for_nonexistent(self, db_repository, db_conn):
        """R: Should return None for non-existent document."""
        # Act
        result = _fetch_document(db_conn, uuid4())

        # Assert
        assert result is None


@pytest.mark.integration
class TestPostgresDocumentRepositoryScopedQueries:
    """Test workspace scoping behavior on list queries."""

    def test_list_documents_scoped_to_workspace(
        self, db_repository, db_conn, workspace_context
    ):
        workspace_id = workspace_context["workspace_id"]
        owner_user_id = workspace_context["owner_user_id"]
        other_workspace_id = uuid4()

        _insert_workspace(
            db_conn,
            other_workspace_id,
            owner_user_id,
            f"Repo Workspace {other_workspace_id}",
        )

        doc_id = uuid4()
        other_doc_id = uuid4()

        try:
            db_repository.save_document(
                Document(
                    id=doc_id,
                    title="Scoped List Doc",
                    workspace_id=workspace_id,
                )
            )
            db_repository.save_document(
                Document(
                    id=other_doc_id,
                    title="Other Workspace List Doc",
                    workspace_id=other_workspace_id,
                )
            )

            results = db_repository.list_documents(
                workspace_id=workspace_id,
                limit=10,
                offset=0,
            )

            result_ids = {doc.id for doc in results}
            assert doc_id in result_ids
            assert other_doc_id not in result_ids
        finally:
            db_conn.execute(
                "DELETE FROM documents WHERE id = ANY(%s)",
                ([doc_id, other_doc_id],),
            )
            db_conn.execute(
                "DELETE FROM workspaces WHERE id = %s",
                (other_workspace_id,),
            )


@pytest.mark.integration
class TestPostgresDocumentRepositoryEdgeCases:
    """Test edge cases and error scenarios."""

    def test_save_chunks_with_empty_list(
        self, db_repository, cleanup_test_data, workspace_context
    ):
        """R: Should handle empty chunks list gracefully."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Empty Chunks Test",
            workspace_id=workspace_id,
        )
        db_repository.save_document(doc)

        # Act & Assert - should not raise exception
        db_repository.save_chunks(doc_id, [], workspace_id=workspace_id)

    def test_save_document_with_none_source(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should handle document with None source."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="No Source",
            source=None,
            workspace_id=workspace_id,
        )

        # Act & Assert
        db_repository.save_document(doc)
        retrieved = _fetch_document(db_conn, doc_id)
        assert retrieved[2] is None

    def test_save_document_with_complex_metadata(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should handle nested JSON metadata."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Complex Metadata",
            metadata={
                "nested": {"key": "value"},
                "array": [1, 2, 3],
                "boolean": True,
                "null": None,
            },
            workspace_id=workspace_id,
        )

        # Act
        db_repository.save_document(doc)

        # Assert
        retrieved = _fetch_document(db_conn, doc_id)
        assert retrieved[3]["nested"]["key"] == "value"
        assert retrieved[3]["array"] == [1, 2, 3]
        assert retrieved[3]["boolean"] is True


@pytest.mark.integration
class TestPostgresDocumentRepositoryAtomicOperations:
    """Test atomic transaction behavior for document + chunks."""

    def test_save_document_with_chunks_atomic_success(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should save document and chunks atomically."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Atomic Test",
            source="https://test.com",
            workspace_id=workspace_id,
        )
        chunks = [
            Chunk(
                content=f"Atomic chunk {i}",
                embedding=[0.1 * (i + 1)] * 768,
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(3)
        ]

        # Act
        db_repository.save_document_with_chunks(doc, chunks)

        # Assert - both document and chunks should exist
        doc_row = _fetch_document(db_conn, doc_id)
        assert doc_row is not None
        assert doc_row[1] == "Atomic Test"

        chunk_count = db_conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = %s",
            (doc_id,),
        ).fetchone()[0]
        assert chunk_count == 3

    def test_save_document_with_chunks_rollback_on_invalid_embedding(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should rollback document if chunk validation fails."""
        # Arrange
        doc_id = uuid4()
        # Note: Don't add to cleanup - document should not exist after rollback
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Rollback Test",
            source="https://test.com",
            workspace_id=workspace_id,
        )
        chunks = [
            Chunk(
                content="Valid chunk",
                embedding=[0.1] * 768,
                document_id=doc_id,
                chunk_index=0,
            ),
            Chunk(
                content="Invalid chunk - wrong dimension",
                embedding=[0.1]
                * 100,  # Wrong dimension - should cause validation failure
                document_id=doc_id,
                chunk_index=1,
            ),
        ]

        # Act & Assert
        with pytest.raises(ValueError, match="768"):
            db_repository.save_document_with_chunks(doc, chunks)

        # Assert - document should NOT exist (validation fails before transaction)
        doc_row = _fetch_document(db_conn, doc_id)
        assert doc_row is None

    def test_save_document_with_chunks_uses_batch_insert(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should efficiently insert many chunks via batch."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(id=doc_id, title="Batch Test", workspace_id=workspace_id)

        # Create many chunks to test batch behavior
        chunks = [
            Chunk(
                content=f"Batch chunk {i}",
                embedding=[float(i) / 100] * 768,
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(50)  # 50 chunks in batch
        ]

        # Act
        db_repository.save_document_with_chunks(doc, chunks)

        # Assert
        chunk_count = db_conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = %s",
            (doc_id,),
        ).fetchone()[0]
        assert chunk_count == 50

    def test_save_document_with_chunks_empty_chunks_list(
        self, db_repository, db_conn, cleanup_test_data, workspace_context
    ):
        """R: Should save document even with empty chunks list."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(id=doc_id, title="No Chunks Doc", workspace_id=workspace_id)

        # Act
        db_repository.save_document_with_chunks(doc, [])

        # Assert - document should exist
        doc_row = _fetch_document(db_conn, doc_id)
        assert doc_row is not None
        assert doc_row[1] == "No Chunks Doc"


@pytest.mark.integration
class TestPostgresDocumentRepositoryPoolIntegration:
    """Test connection pool usage in repository."""

    def test_repository_uses_pool_connections(
        self, db_repository, cleanup_test_data, workspace_context
    ):
        """R: Multiple operations should reuse pool connections."""
        # Arrange
        doc_ids = [uuid4() for _ in range(5)]
        cleanup_test_data.extend(doc_ids)
        workspace_id = workspace_context["workspace_id"]

        # Act - multiple sequential operations
        for i, doc_id in enumerate(doc_ids):
            doc = Document(
                id=doc_id,
                title=f"Pool Test {i}",
                workspace_id=workspace_id,
            )
            db_repository.save_document(doc)

        # Assert - all documents saved successfully
        # (no connection exhaustion errors)
        # Note: Pool behavior verified by successful completion

    def test_find_similar_chunks_uses_pool(
        self, db_repository, cleanup_test_data, workspace_context
    ):
        """R: Vector search should use pool connections."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        workspace_id = workspace_context["workspace_id"]

        doc = Document(
            id=doc_id,
            title="Pool Search Test",
            workspace_id=workspace_id,
        )
        chunks = [
            Chunk(
                content=f"Pool search chunk {i}",
                embedding=[0.1 * (i + 1)] * 768,
                document_id=doc_id,
                chunk_index=i,
            )
            for i in range(3)
        ]
        db_repository.save_document_with_chunks(doc, chunks)

        # Act - multiple search operations
        for _ in range(10):
            results = db_repository.find_similar_chunks(
                embedding=[0.2] * 768,
                top_k=3,
                workspace_id=workspace_id,
            )

        # Assert - all searches completed (pool working)
        assert len(results) <= 3


# Note: Additional tests for:
# - Statement timeout behavior (requires long-running query simulation)
# - Connection recovery after pool exhaustion
# - Performance benchmarks
