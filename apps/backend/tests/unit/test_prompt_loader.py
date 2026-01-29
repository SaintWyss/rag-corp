"""
Name: Prompt Loader Unit Tests

Responsibilities:
  - Test PromptLoader class
  - Verify version selection
  - Test file not found handling
  - Test template formatting

Notes:
  - Uses temp files for isolated testing
  - Tests caching behavior
"""

import pytest

from app.infrastructure.prompts.loader import PromptLoader


@pytest.mark.unit
class TestPromptLoader:
    """Test suite for PromptLoader class."""

    def test_loader_default_version(self):
        """R: Should default to v1 version."""
        loader = PromptLoader()

        assert loader.version == "v1"

    def test_loader_custom_version(self):
        """R: Should accept custom version."""
        loader = PromptLoader(version="v2")

        assert loader.version == "v2"

    def test_loader_loads_existing_template(self):
        """R: Should load existing v1 template."""
        loader = PromptLoader(version="v1")

        template = loader.get_template()

        assert template is not None
        assert "{context}" in template
        assert "{query}" in template
        assert "CONTEXTO" in template  # Spanish

    def test_loader_caches_template(self):
        """R: Should cache template after first load."""
        loader = PromptLoader(version="v1")

        # First call loads from file
        template1 = loader.get_template()

        # Second call should use cache
        template2 = loader.get_template()

        assert template1 is template2  # Same object (cached)

    def test_loader_format_replaces_placeholders(self):
        """R: Should replace {context} and {query} placeholders."""
        loader = PromptLoader(version="v1")

        formatted = loader.format(
            context="This is the context", query="What is the answer?"
        )

        assert "This is the context" in formatted
        assert "What is the answer?" in formatted
        assert "{context}" not in formatted
        assert "{query}" not in formatted

    def test_loader_file_not_found_raises(self):
        """R: Should raise FileNotFoundError for missing version."""
        loader = PromptLoader(version="nonexistent_version")

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.get_template()

        assert "nonexistent_version" in str(exc_info.value)


@pytest.mark.unit
class TestPromptLoaderSingleton:
    """Test suite for get_prompt_loader singleton."""

    def test_get_prompt_loader_uses_settings(self, monkeypatch):
        """R: Should use prompt_version from settings."""
        # Clear the lru_cache
        from app.infrastructure.prompts.loader import get_prompt_loader

        get_prompt_loader.cache_clear()

        # Mock settings via monkeypatch on config module
        monkeypatch.setenv("PROMPT_VERSION", "v1")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        # Clear settings cache to pick up new env
        from app.crosscutting.config import get_settings

        get_settings.cache_clear()

        loader = get_prompt_loader()

        assert loader.version == "v1"

        # Clear caches after test
        get_prompt_loader.cache_clear()
        get_settings.cache_clear()


@pytest.mark.unit
class TestPromptTemplateContent:
    """Test suite for v1 prompt template content."""

    def test_v1_template_has_security_rules(self):
        """R: Should contain security rules against injection."""
        loader = PromptLoader(version="v1")
        template = loader.get_template()

        # Check for security-related content
        assert "NUNCA" in template or "NEVER" in template
        assert "instrucciones" in template.lower() or "instructions" in template.lower()

    def test_v1_template_has_spanish_response_rule(self):
        """R: Should instruct to respond in Spanish."""
        loader = PromptLoader(version="v1")
        template = loader.get_template()

        assert "español" in template.lower() or "spanish" in template.lower()

    def test_v1_template_has_grounding_instructions(self):
        """R: Should instruct to cite sources when possible."""
        loader = PromptLoader(version="v1")
        template = loader.get_template()

        assert "fuente" in template.lower() or "cita" in template.lower()
