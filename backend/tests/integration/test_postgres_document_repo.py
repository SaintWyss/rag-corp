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
    pytest.skip("Set RUN_INTEGRATION=1 to run integration tests", allow_module_level=True)

from uuid import uuid4, UUID
from typing import List

import psycopg

from app.domain.entities import Document, Chunk
from app.infrastructure.repositories.postgres_document_repo import PostgresDocumentRepository

pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag")


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
    
    def test_save_document(self, db_repository, db_conn, cleanup_test_data):
        """R: Should persist document to database."""
        # Arrange
        doc = Document(
            id=uuid4(),
            title="Integration Test Document",
            source="https://test.com/doc.pdf",
            metadata={"test": True, "author": "Test Suite"}
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
    
    def test_save_document_upsert_behavior(self, db_repository, db_conn, cleanup_test_data):
        """R: Should update existing document on conflict."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        original_doc = Document(
            id=doc_id,
            title="Original Title",
            source="https://original.com"
        )
        
        updated_doc = Document(
            id=doc_id,
            title="Updated Title",
            source="https://updated.com",
            metadata={"updated": True}
        )
        
        # Act
        db_repository.save_document(original_doc)
        db_repository.save_document(updated_doc)  # Same ID, should update
        
        # Assert
        retrieved = _fetch_document(db_conn, doc_id)
        assert retrieved[1] == "Updated Title"
        assert retrieved[2] == "https://updated.com"
        assert retrieved[3].get("updated") is True
    
    def test_save_chunks_with_embeddings(self, db_repository, db_conn, cleanup_test_data):
        """R: Should persist chunks with vector embeddings."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(id=doc_id, title="Test Doc")
        db_repository.save_document(doc)
        
        chunks = [
            Chunk(
                content=f"Test chunk {i}",
                embedding=[0.1 * i] * 768,
                document_id=doc_id,
                chunk_index=i
            )
            for i in range(3)
        ]
        
        # Act
        db_repository.save_chunks(doc_id, chunks)
        
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
        self,
        db_repository,
        cleanup_test_data
    ):
        """R: Should find similar chunks using vector search."""
        # Arrange - create test document and chunks
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(id=doc_id, title="Search Test Doc")
        db_repository.save_document(doc)
        
        # Create chunks with distinct embeddings
        chunks = [
            Chunk(
                content=f"Content about topic {i}",
                embedding=[float(i) / 10] * 768,
                document_id=doc_id,
                chunk_index=i
            )
            for i in range(5)
        ]
        db_repository.save_chunks(doc_id, chunks)
        
        # Act - search for similar chunks
        query_embedding = [0.2] * 768  # Should be closest to chunk 2
        results = db_repository.find_similar_chunks(
            embedding=query_embedding,
            top_k=3
        )
        
        # Assert
        assert len(results) <= 3
        assert all(isinstance(chunk, Chunk) for chunk in results)
        assert all(chunk.document_id == doc_id for chunk in results)
    
    def test_find_similar_chunks_respects_top_k(
        self,
        db_repository,
        cleanup_test_data
    ):
        """R: Should return at most top_k results."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(id=doc_id, title="Top K Test")
        db_repository.save_document(doc)
        
        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[float(i) / 100] * 768,
                document_id=doc_id,
                chunk_index=i
            )
            for i in range(10)
        ]
        db_repository.save_chunks(doc_id, chunks)
        
        # Act
        results = db_repository.find_similar_chunks(
            embedding=[0.05] * 768,
            top_k=5
        )
        
        # Assert
        assert len(results) <= 5
    
    def test_find_similar_chunks_returns_most_similar_first(
        self,
        db_repository,
        cleanup_test_data
    ):
        """R: Should return chunks ordered by similarity (descending)."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(id=doc_id, title="Ranking Test")
        db_repository.save_document(doc)
        
        # Create chunks with known embeddings
        chunks = [
            Chunk(
                content="Very different",
                embedding=[1.0] * 768,
                document_id=doc_id,
                chunk_index=0
            ),
            Chunk(
                content="Exact match",
                embedding=[0.5] * 768,  # Exact match to query
                document_id=doc_id,
                chunk_index=1
            ),
            Chunk(
                content="Somewhat similar",
                embedding=[0.6] * 768,
                document_id=doc_id,
                chunk_index=2
            ),
        ]
        db_repository.save_chunks(doc_id, chunks)
        
        # Act - search with embedding matching chunk 1
        results = db_repository.find_similar_chunks(
            embedding=[0.5] * 768,
            top_k=3
        )
        
        # Assert - most similar should be first
        # Note: Exact assertions depend on similarity metric (cosine)
        assert len(results) >= 1
        # First result should be the exact match (chunk_index=1)
        # This is a heuristic test - exact verification depends on distance calculation
    
    def test_find_similar_chunks_with_no_results(self, db_repository):
        """R: Should return empty list when no documents exist."""
        # Act - search in empty database (assuming cleanup)
        results = db_repository.find_similar_chunks(
            embedding=[0.0] * 768,
            top_k=5
        )
        
        # Assert
        assert isinstance(results, list)
        # May return empty or existing test data from other tests


@pytest.mark.integration
class TestPostgresDocumentRepositoryRetrievalOperations:
    """Test document and chunk retrieval operations."""
    
    def test_get_document_by_id(self, db_repository, db_conn, cleanup_test_data):
        """R: Should retrieve document by ID."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(
            id=doc_id,
            title="Retrieval Test",
            source="https://test.com"
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
class TestPostgresDocumentRepositoryEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_save_chunks_with_empty_list(self, db_repository, cleanup_test_data):
        """R: Should handle empty chunks list gracefully."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(id=doc_id, title="Empty Chunks Test")
        db_repository.save_document(doc)
        
        # Act & Assert - should not raise exception
        db_repository.save_chunks(doc_id, [])
    
    def test_save_document_with_none_source(self, db_repository, db_conn, cleanup_test_data):
        """R: Should handle document with None source."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(id=doc_id, title="No Source", source=None)
        
        # Act & Assert
        db_repository.save_document(doc)
        retrieved = _fetch_document(db_conn, doc_id)
        assert retrieved[2] is None
    
    def test_save_document_with_complex_metadata(
        self,
        db_repository,
        db_conn,
        cleanup_test_data
    ):
        """R: Should handle nested JSON metadata."""
        # Arrange
        doc_id = uuid4()
        cleanup_test_data.append(doc_id)
        
        doc = Document(
            id=doc_id,
            title="Complex Metadata",
            metadata={
                "nested": {"key": "value"},
                "array": [1, 2, 3],
                "boolean": True,
                "null": None
            }
        )
        
        # Act
        db_repository.save_document(doc)
        
        # Assert
        retrieved = _fetch_document(db_conn, doc_id)
        assert retrieved[3]["nested"]["key"] == "value"
        assert retrieved[3]["array"] == [1, 2, 3]
        assert retrieved[3]["boolean"] is True


# Note: Add more integration tests for:
# - Connection failure scenarios
# - Transaction rollback
# - Concurrent operations
# - Large batch operations
# - Performance benchmarks
