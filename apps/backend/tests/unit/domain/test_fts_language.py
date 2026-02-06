"""
Name: FTS Language Validation Unit Tests

Responsibilities:
  - Verify validate_fts_language returns valid languages unchanged.
  - Verify invalid/None/empty values fall back to default.
  - Verify FTS_ALLOWED_LANGUAGES is immutable (frozenset).
  - Verify Workspace entity default fts_language.
"""

from uuid import uuid4

import pytest
from app.domain.entities import (
    FTS_ALLOWED_LANGUAGES,
    FTS_DEFAULT_LANGUAGE,
    Workspace,
    validate_fts_language,
)

pytestmark = pytest.mark.unit


class TestValidateFtsLanguage:
    @pytest.mark.parametrize("lang", ["spanish", "english", "simple"])
    def test_valid_values_returned_unchanged(self, lang: str):
        assert validate_fts_language(lang) == lang

    def test_invalid_returns_default(self):
        assert validate_fts_language("klingon") == FTS_DEFAULT_LANGUAGE

    def test_none_returns_default(self):
        assert validate_fts_language(None) == FTS_DEFAULT_LANGUAGE

    def test_empty_returns_default(self):
        assert validate_fts_language("") == FTS_DEFAULT_LANGUAGE

    def test_default_language_is_spanish(self):
        assert FTS_DEFAULT_LANGUAGE == "spanish"


class TestFtsAllowedLanguages:
    def test_is_frozenset(self):
        assert isinstance(FTS_ALLOWED_LANGUAGES, frozenset)

    def test_contains_expected_values(self):
        assert FTS_ALLOWED_LANGUAGES == {"spanish", "english", "simple"}


class TestWorkspaceEntityFtsLanguage:
    def test_default_fts_language(self):
        ws = Workspace(id=uuid4(), name="test")
        assert ws.fts_language == "spanish"

    def test_custom_fts_language(self):
        ws = Workspace(id=uuid4(), name="test", fts_language="english")
        assert ws.fts_language == "english"
