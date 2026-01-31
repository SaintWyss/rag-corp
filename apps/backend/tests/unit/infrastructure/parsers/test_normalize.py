import pytest
from app.infrastructure.parsers.normalize import normalize_text, truncate_text


def test_normalize_text_removes_null_bytes():
    raw = "Hello\x00World"
    assert normalize_text(raw, collapse_whitespace=False) == "HelloWorld"


def test_normalize_text_strips_whitespace():
    raw = "  Hello World  "
    assert normalize_text(raw, collapse_whitespace=False) == "Hello World"


def test_normalize_text_collapses_excessive_whitespace():
    raw = "Hello    World\n\n\nNew    Line"
    # Should reduce spaces to 1, and newlines to max 2
    normalized = normalize_text(raw, collapse_whitespace=True)
    assert normalized == "Hello World\n\nNew Line"


def test_normalize_text_handles_empty_input():
    assert normalize_text(None, collapse_whitespace=True) == ""
    assert normalize_text("", collapse_whitespace=True) == ""


def test_truncate_text_respects_limit():
    text = "Hello World"
    truncated, was_cut = truncate_text(text, max_chars=5)
    assert truncated == "Hello"
    assert was_cut is True


def test_truncate_text_no_truncation_needed():
    text = "Hello"
    truncated, was_cut = truncate_text(text, max_chars=10)
    assert truncated == "Hello"
    assert was_cut is False


def test_truncate_text_handles_none_limit():
    text = "Hello World"
    # max_chars=None means no limit
    truncated, was_cut = truncate_text(text, max_chars=None)
    assert truncated == "Hello World"
    assert was_cut is False
