"""
Name: Database Pool Tests

Responsibilities:
  - Test pool lifecycle (init, get, close, reset)
  - Test embedding validation
  - Offline unit tests (no real DB)

Notes:
  - Uses mocking for ConnectionPool
  - Tests pool singleton behavior
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestPoolLifecycle:
    """Test pool initialization and cleanup."""

    def test_init_pool_creates_pool(self):
        """init_pool should create a ConnectionPool."""
        from app.infrastructure.db.pool import init_pool, reset_pool

        reset_pool()  # Clean state

        with patch("app.infrastructure.db.pool.ConnectionPool") as MockPool:
            mock_pool = MagicMock()
            MockPool.return_value = mock_pool

            result = init_pool("postgresql://test", min_size=2, max_size=10)

            MockPool.assert_called_once()
            assert result == mock_pool

        reset_pool()

    def test_init_pool_twice_raises_error(self):
        """init_pool called twice should raise RuntimeError."""
        from app.infrastructure.db.pool import init_pool, reset_pool

        reset_pool()

        with patch("app.infrastructure.db.pool.ConnectionPool") as MockPool:
            mock_pool = MagicMock()
            MockPool.return_value = mock_pool

            init_pool("postgresql://test", min_size=2, max_size=10)

            with pytest.raises(RuntimeError, match="already initialized"):
                init_pool("postgresql://test", min_size=2, max_size=10)

        reset_pool()

    def test_get_pool_without_init_raises_error(self):
        """get_pool before init_pool should raise RuntimeError."""
        from app.infrastructure.db.pool import get_pool, reset_pool

        reset_pool()

        with pytest.raises(RuntimeError, match="not initialized"):
            get_pool()

    def test_close_pool_clears_singleton(self):
        """close_pool should clear the singleton."""
        from app.infrastructure.db.pool import (
            close_pool,
            get_pool,
            init_pool,
            reset_pool,
        )

        reset_pool()

        with patch("app.infrastructure.db.pool.ConnectionPool") as MockPool:
            mock_pool = MagicMock()
            MockPool.return_value = mock_pool

            init_pool("postgresql://test", min_size=2, max_size=10)
            close_pool()

            mock_pool.close.assert_called_once()

            with pytest.raises(RuntimeError, match="not initialized"):
                get_pool()

        reset_pool()

    def test_reset_pool_allows_reinit(self):
        """reset_pool should allow re-initialization."""
        from app.infrastructure.db.pool import init_pool, reset_pool

        reset_pool()

        with patch("app.infrastructure.db.pool.ConnectionPool") as MockPool:
            mock_pool = MagicMock()
            MockPool.return_value = mock_pool

            init_pool("postgresql://test", min_size=2, max_size=10)
            reset_pool()

            # Should not raise
            init_pool("postgresql://test", min_size=2, max_size=10)

        reset_pool()


@pytest.mark.unit
class TestEmbeddingValidation:
    """Test embedding dimension validation in repository."""

    def test_validate_embeddings_correct_dimension(self):
        """768D embeddings should pass validation."""
        from app.domain.entities import Chunk
        from app.infrastructure.repositories.postgres.document import (
            PostgresDocumentRepository,
        )

        repo = PostgresDocumentRepository(pool=MagicMock())

        chunks = [
            Chunk(content="test", embedding=[0.1] * 768),
            Chunk(content="test2", embedding=[0.2] * 768),
        ]

        # Should not raise
        repo._validate_embeddings(chunks)

    def test_validate_embeddings_wrong_dimension_raises(self):
        """Non-768D embeddings should raise ValueError."""
        from app.domain.entities import Chunk
        from app.infrastructure.repositories.postgres.document import (
            PostgresDocumentRepository,
        )

        repo = PostgresDocumentRepository(pool=MagicMock())

        chunks = [
            Chunk(content="test", embedding=[0.1] * 100),  # Wrong dimension
        ]

        with pytest.raises(ValueError, match="768"):
            repo._validate_embeddings(chunks)

    def test_validate_embeddings_none_embedding_raises(self):
        """Chunk without embedding should raise ValueError."""
        from app.domain.entities import Chunk
        from app.infrastructure.repositories.postgres.document import (
            PostgresDocumentRepository,
        )

        repo = PostgresDocumentRepository(pool=MagicMock())

        chunks = [
            Chunk(content="test", embedding=None),
        ]

        with pytest.raises(ValueError, match="embedding is required"):
            repo._validate_embeddings(chunks)


@pytest.mark.unit
class TestRepositoryPoolUsage:
    """Test repository uses pool correctly."""

    def test_repository_uses_injected_pool(self):
        """Repository should use injected pool."""
        from app.infrastructure.repositories.postgres.document import (
            PostgresDocumentRepository,
        )

        mock_pool = MagicMock()
        repo = PostgresDocumentRepository(pool=mock_pool)

        assert repo._get_pool() == mock_pool

    def test_repository_falls_back_to_global_pool(self):
        """Repository without injected pool uses global."""
        from app.infrastructure.db.pool import init_pool, reset_pool
        from app.infrastructure.repositories.postgres.document import (
            PostgresDocumentRepository,
        )

        reset_pool()

        with patch("app.infrastructure.db.pool.ConnectionPool") as MockPool:
            mock_pool = MagicMock()
            MockPool.return_value = mock_pool

            init_pool("postgresql://test", min_size=2, max_size=10)

            repo = PostgresDocumentRepository()  # No pool injected

            assert repo._get_pool() == mock_pool

        reset_pool()
