"""
Unit tests for app/config.py (Settings validation).

Tests:
  - Valid configuration with all required env vars
  - Default values are applied correctly
  - chunk_size validation (must be > 0)
  - chunk_overlap validation (must be >= 0 and < chunk_size)
  - Cross-field validation (overlap < chunk_size)
  - get_allowed_origins_list parsing

Note:
  - Uses monkeypatch to set environment variables
  - Tests should NOT require actual database/API connections
"""

import pytest
from unittest.mock import patch
import os


pytestmark = pytest.mark.unit  # Apply to all tests in this module


class TestSettings:
    """Test Settings class validation."""

    def test_valid_settings_with_defaults(self, monkeypatch):
        """Settings loads correctly with required vars and applies defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        
        # Clear cache to force reload
        from app.config import get_settings, Settings
        get_settings.cache_clear()
        
        settings = Settings()
        
        assert settings.database_url == "postgresql://test:test@localhost/test"
        assert settings.google_api_key == "test-api-key"
        assert settings.chunk_size == 900
        assert settings.chunk_overlap == 120
        assert settings.max_top_k == 20
        assert settings.max_ingest_chars == 100_000
        assert settings.max_query_chars == 2_000
        assert settings.max_title_chars == 200
        assert settings.max_source_chars == 500

    def test_custom_chunk_settings(self, monkeypatch):
        """Settings respects custom chunk configuration."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "500")
        monkeypatch.setenv("CHUNK_OVERLAP", "50")
        
        from app.config import Settings
        settings = Settings()
        
        assert settings.chunk_size == 500
        assert settings.chunk_overlap == 50

    def test_chunk_size_must_be_positive(self, monkeypatch):
        """chunk_size <= 0 raises ValidationError."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "0")
        
        from pydantic import ValidationError
        from app.config import Settings
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "chunk_size must be greater than 0" in str(exc_info.value)

    def test_chunk_size_negative_fails(self, monkeypatch):
        """Negative chunk_size raises ValidationError."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "-100")
        
        from pydantic import ValidationError
        from app.config import Settings
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "chunk_size must be greater than 0" in str(exc_info.value)

    def test_chunk_overlap_negative_fails(self, monkeypatch):
        """Negative chunk_overlap raises ValidationError."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_OVERLAP", "-10")
        
        from pydantic import ValidationError
        from app.config import Settings
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "chunk_overlap must be >= 0" in str(exc_info.value)

    def test_overlap_equals_chunk_size_fails(self, monkeypatch):
        """overlap == chunk_size raises ValueError on validate_chunk_params."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "500")
        monkeypatch.setenv("CHUNK_OVERLAP", "500")
        
        from app.config import Settings
        
        settings = Settings()  # This passes field validation
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate_chunk_params()  # This catches cross-field
        
        assert "chunk_overlap (500) must be less than chunk_size (500)" in str(exc_info.value)

    def test_overlap_greater_than_chunk_size_fails(self, monkeypatch):
        """overlap > chunk_size raises ValueError on validate_chunk_params."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "500")
        monkeypatch.setenv("CHUNK_OVERLAP", "600")
        
        from app.config import Settings
        
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate_chunk_params()
        
        assert "chunk_overlap (600) must be less than chunk_size (500)" in str(exc_info.value)

    def test_get_settings_validates_chunk_params(self, monkeypatch):
        """get_settings() calls validate_chunk_params automatically."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "100")
        monkeypatch.setenv("CHUNK_OVERLAP", "100")  # Invalid: equals chunk_size
        
        from app.config import get_settings
        get_settings.cache_clear()
        
        with pytest.raises(ValueError) as exc_info:
            get_settings()
        
        assert "must be less than chunk_size" in str(exc_info.value)

    def test_get_allowed_origins_list_single(self, monkeypatch):
        """Single origin is parsed correctly."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
        
        from app.config import Settings
        settings = Settings()
        
        assert settings.get_allowed_origins_list() == ["http://localhost:3000"]

    def test_get_allowed_origins_list_multiple(self, monkeypatch):
        """Multiple origins are parsed correctly."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000, https://app.example.com , http://dev.local")
        
        from app.config import Settings
        settings = Settings()
        
        origins = settings.get_allowed_origins_list()
        assert origins == [
            "http://localhost:3000",
            "https://app.example.com",
            "http://dev.local",
        ]

    def test_missing_required_env_raises(self, monkeypatch):
        """Missing DATABASE_URL or GOOGLE_API_KEY raises ValidationError."""
        # Clear all relevant env vars
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        
        from pydantic import ValidationError
        from app.config import Settings
        
        with pytest.raises(ValidationError):
            Settings()

    def test_zero_overlap_is_valid(self, monkeypatch):
        """overlap=0 is a valid configuration (no overlap)."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("CHUNK_SIZE", "500")
        monkeypatch.setenv("CHUNK_OVERLAP", "0")
        
        from app.config import Settings
        settings = Settings()
        settings.validate_chunk_params()  # Should not raise
        
        assert settings.chunk_overlap == 0


class TestChunkerValidation:
    """Test SimpleTextChunker parameter validation."""

    def test_chunker_rejects_zero_chunk_size(self):
        """chunk_size=0 raises ValueError."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        with pytest.raises(ValueError) as exc_info:
            SimpleTextChunker(chunk_size=0, overlap=0)
        
        assert "chunk_size must be > 0" in str(exc_info.value)

    def test_chunker_rejects_negative_chunk_size(self):
        """Negative chunk_size raises ValueError."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        with pytest.raises(ValueError) as exc_info:
            SimpleTextChunker(chunk_size=-100, overlap=0)
        
        assert "chunk_size must be > 0" in str(exc_info.value)

    def test_chunker_rejects_negative_overlap(self):
        """Negative overlap raises ValueError."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        with pytest.raises(ValueError) as exc_info:
            SimpleTextChunker(chunk_size=500, overlap=-10)
        
        assert "overlap must be >= 0" in str(exc_info.value)

    def test_chunker_rejects_overlap_equals_chunk_size(self):
        """overlap == chunk_size raises ValueError."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        with pytest.raises(ValueError) as exc_info:
            SimpleTextChunker(chunk_size=500, overlap=500)
        
        assert "overlap (500) must be less than chunk_size (500)" in str(exc_info.value)

    def test_chunker_rejects_overlap_greater_than_chunk_size(self):
        """overlap > chunk_size raises ValueError."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        with pytest.raises(ValueError) as exc_info:
            SimpleTextChunker(chunk_size=500, overlap=600)
        
        assert "overlap (600) must be less than chunk_size (500)" in str(exc_info.value)

    def test_chunker_accepts_valid_params(self):
        """Valid parameters create chunker successfully."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        chunker = SimpleTextChunker(chunk_size=500, overlap=100)
        
        assert chunker.chunk_size == 500
        assert chunker.overlap == 100

    def test_chunker_accepts_zero_overlap(self):
        """overlap=0 is valid (no overlap between chunks)."""
        from app.infrastructure.text.chunker import SimpleTextChunker
        
        chunker = SimpleTextChunker(chunk_size=500, overlap=0)
        
        assert chunker.overlap == 0


@pytest.mark.unit
class TestDatabasePoolSettings:
    """Test database pool configuration settings."""

    def test_default_pool_settings(self, monkeypatch):
        """Default pool settings should have sensible values."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        
        from app.config import Settings
        settings = Settings()
        
        assert settings.db_pool_min_size == 2
        assert settings.db_pool_max_size == 10
        assert settings.db_statement_timeout_ms == 30000

    def test_custom_pool_settings(self, monkeypatch):
        """Pool settings should be configurable via env vars."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("DB_POOL_MIN_SIZE", "5")
        monkeypatch.setenv("DB_POOL_MAX_SIZE", "20")
        monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MS", "60000")
        
        from app.config import Settings
        settings = Settings()
        
        assert settings.db_pool_min_size == 5
        assert settings.db_pool_max_size == 20
        assert settings.db_statement_timeout_ms == 60000

    def test_zero_timeout_disables_timeout(self, monkeypatch):
        """Statement timeout of 0 should disable the timeout."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MS", "0")
        
        from app.config import Settings
        settings = Settings()
        
        assert settings.db_statement_timeout_ms == 0
