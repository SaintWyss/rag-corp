"""
Name: Content Hash Utility Unit Tests

Responsibilities:
  - Verify normalize_text handles NFC, trim, whitespace collapse
  - Verify normalize_text preserves case (NO lowercase)
  - Verify compute_content_hash is deterministic and workspace-scoped
  - Verify compute_file_hash is deterministic and workspace-scoped
  - Verify output format (hex string, 64 chars)
"""

from __future__ import annotations

import re
from uuid import UUID

import pytest
from app.application.content_hash import (
    compute_content_hash,
    compute_file_hash,
    normalize_text,
)

pytestmark = pytest.mark.unit

_WS1 = UUID("00000000-0000-0000-0000-000000000001")
_WS2 = UUID("00000000-0000-0000-0000-000000000002")


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_strips_leading_and_trailing_whitespace(self):
        assert normalize_text("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_collapses_tabs_and_newlines(self):
        assert normalize_text("hello\t\tworld\n\nfoo") == "hello world foo"

    def test_nfc_normalization(self):
        # é as combining e + acute (NFD) should normalize to single codepoint (NFC)
        nfd_e = "e\u0301"  # NFD form
        nfc_e = "\u00e9"  # NFC form
        assert normalize_text(nfd_e) == nfc_e

    def test_preserves_case(self):
        result = normalize_text("Hello World UPPER lower")
        assert result == "Hello World UPPER lower"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_whitespace_only(self):
        assert normalize_text("   \t\n  ") == ""


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    def test_deterministic_same_input(self):
        h1 = compute_content_hash(_WS1, "hello world")
        h2 = compute_content_hash(_WS1, "hello world")
        assert h1 == h2

    def test_different_workspace_different_hash(self):
        h1 = compute_content_hash(_WS1, "same content")
        h2 = compute_content_hash(_WS2, "same content")
        assert h1 != h2

    def test_different_content_different_hash(self):
        h1 = compute_content_hash(_WS1, "content A")
        h2 = compute_content_hash(_WS1, "content B")
        assert h1 != h2

    def test_output_is_hex_64_chars(self):
        h = compute_content_hash(_WS1, "test content")
        assert len(h) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", h)

    def test_whitespace_variants_produce_same_hash(self):
        h1 = compute_content_hash(_WS1, "hello   world")
        h2 = compute_content_hash(_WS1, "hello\t\nworld")
        assert h1 == h2

    def test_case_sensitive(self):
        h1 = compute_content_hash(_WS1, "Hello")
        h2 = compute_content_hash(_WS1, "hello")
        assert h1 != h2


# ---------------------------------------------------------------------------
# compute_file_hash
# ---------------------------------------------------------------------------


class TestComputeFileHash:
    def test_deterministic_same_bytes(self):
        data = b"pdf-binary-content-here"
        h1 = compute_file_hash(_WS1, data)
        h2 = compute_file_hash(_WS1, data)
        assert h1 == h2

    def test_different_workspace_different_hash(self):
        data = b"same bytes"
        h1 = compute_file_hash(_WS1, data)
        h2 = compute_file_hash(_WS2, data)
        assert h1 != h2

    def test_different_bytes_different_hash(self):
        h1 = compute_file_hash(_WS1, b"file-a")
        h2 = compute_file_hash(_WS1, b"file-b")
        assert h1 != h2

    def test_output_is_hex_64_chars(self):
        h = compute_file_hash(_WS1, b"test")
        assert len(h) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", h)
