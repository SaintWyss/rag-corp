"""
Name: Pytest Configuration and Shared Fixtures

Responsibilities:
  - Provide reusable test fixtures
  - Mock external dependencies (DB, Google API)
  - Configure test environment
  - Setup test data factories

Collaborators:
  - pytest: Test framework
  - unittest.mock: Mocking library
  - app.domain: Domain entities and protocols

Notes:
  - Fixtures are auto-discovered by pytest
  - Use @pytest.fixture(scope="function") for per-test isolation
  - Use @pytest.fixture(scope="session") for expensive setup
"""

# IMPORTANT: Suppress NumPy reload warning BEFORE any imports that load numpy
import warnings

warnings.filterwarnings(
    "ignore", message=".*NumPy module was reloaded.*", category=UserWarning
)

import os
import sys
from pathlib import Path
from typing import List
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.crosscutting import config as app_config  # noqa: E402

app_config.Settings.model_config["env_file"] = None

from app.domain.entities import Chunk, Document, QueryResult  # noqa: E402
from app.domain.repositories import DocumentRepository  # noqa: E402
from app.domain.services import EmbeddingService, LLMService  # noqa: E402

os.environ.setdefault("APP_ENV", "test")


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )


# ============================================================================
# Domain Entity Fixtures
# ============================================================================


@pytest.fixture
def sample_document() -> Document:
    """R: Create a sample document for testing."""
    return Document(
        id=uuid4(),
        title="Test Document",
        source="https://example.com/doc.pdf",
        metadata={"author": "Test Author", "year": 2025},
    )


@pytest.fixture
def sample_chunk(sample_document: Document) -> Chunk:
    """R: Create a sample chunk for testing."""
    return Chunk(
        content="This is a test chunk with sample content.",
        embedding=[0.1] * 768,  # 768-dimensional vector
        document_id=sample_document.id,
        chunk_index=0,
        chunk_id=uuid4(),
    )


@pytest.fixture
def sample_chunks(sample_document: Document) -> List[Chunk]:
    """R: Create multiple chunks for testing retrieval."""
    return [
        Chunk(
            content=f"Chunk {i} content for testing.",
            embedding=[0.1 * i] * 768,
            document_id=sample_document.id,
            chunk_index=i,
            chunk_id=uuid4(),
        )
        for i in range(3)
    ]


@pytest.fixture
def sample_query_result(sample_chunks: List[Chunk]) -> QueryResult:
    """R: Create a sample query result for testing."""
    return QueryResult(
        answer="This is a generated answer based on context.",
        chunks=sample_chunks,
        query="What is the test about?",
    )


# ============================================================================
# Mock Repository Fixtures
# ============================================================================


@pytest.fixture
def mock_repository(sample_chunks: List[Chunk]) -> Mock:
    """
    R: Create a mock DocumentRepository.

    Pre-configured behaviors:
    - find_similar_chunks() returns sample_chunks
    - find_similar_chunks_mmr() returns sample_chunks (MMR diversity)
    - save_document() succeeds
    - save_chunks() succeeds
    """
    mock = Mock(spec=DocumentRepository)

    # Configure default return values
    mock.find_similar_chunks.return_value = sample_chunks
    mock.find_similar_chunks_mmr.return_value = sample_chunks  # MMR diversity search
    mock.save_document.return_value = None
    mock.save_chunks.return_value = None

    return mock


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_embedding_service() -> Mock:
    """
    R: Create a mock EmbeddingService.

    Pre-configured behaviors:
    - embed_query() returns 768-dimensional vector
    - embed_batch() returns list of vectors
    """
    mock = Mock(spec=EmbeddingService)

    # Single embedding for query
    mock.embed_query.return_value = [0.5] * 768

    # Batch embeddings
    def embed_batch_side_effect(texts: List[str]) -> List[List[float]]:
        return [[0.5 + i * 0.1] * 768 for i in range(len(texts))]

    mock.embed_batch.side_effect = embed_batch_side_effect

    return mock


@pytest.fixture
def mock_llm_service() -> Mock:
    """
    R: Create a mock LLMService.

    Pre-configured behaviors:
    - generate_answer() returns simple "Generated answer" by default
    - Can be overridden with return_value or side_effect in tests
    """
    mock = Mock(spec=LLMService)

    # Default RAG generation (can be overridden in tests)
    mock.generate_answer.return_value = "Generated answer"

    # Add prompt_version attribute for observability
    mock.prompt_version = "v1"

    return mock


@pytest.fixture
def mock_context_builder() -> Mock:
    """
    R: Create a mock ContextBuilder.

    Pre-configured behaviors:
    - build() returns assembled context and chunks_used count
    """
    mock = Mock()

    def build_side_effect(chunks):
        """Assemble context from chunks with [S#] format."""
        if not chunks:
            return "", 0
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"---[S{i + 1}]---\n{chunk.content}")
        return "\n\n".join(context_parts), len(chunks)

    mock.build.side_effect = build_side_effect
    return mock


# ============================================================================
# Environment and Configuration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """R: Provide test database URL (for integration tests)."""
    return "postgresql://postgres:postgres@localhost:5432/rag_test"


@pytest.fixture
def mock_google_api_key(monkeypatch) -> None:
    """R: Mock Google API key environment variable."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key-12345")


# ============================================================================
# Test Data Factories
# ============================================================================


class DocumentFactory:
    """R: Factory for creating test documents with custom attributes."""

    @staticmethod
    def create(
        title: str = "Test Document",
        source: str | None = None,
        metadata: dict | None = None,
    ) -> Document:
        return Document(id=uuid4(), title=title, source=source, metadata=metadata or {})


class ChunkFactory:
    """R: Factory for creating test chunks with custom attributes."""

    @staticmethod
    def create(
        content: str = "Test chunk content",
        document_id: UUID | None = None,
        chunk_index: int = 0,
        embedding: List[float] | None = None,
    ) -> Chunk:
        return Chunk(
            content=content,
            embedding=embedding or [0.1] * 768,
            document_id=document_id or uuid4(),
            chunk_index=chunk_index,
            chunk_id=uuid4(),
        )


@pytest.fixture
def document_factory() -> type[DocumentFactory]:
    """R: Provide DocumentFactory for tests."""
    return DocumentFactory


@pytest.fixture
def chunk_factory() -> type[ChunkFactory]:
    """R: Provide ChunkFactory for tests."""
    return ChunkFactory
