"""Unit tests for pagination utilities."""

from app.platform.pagination import encode_cursor, decode_cursor, paginate


class TestCursor:
    """Test cursor encoding/decoding."""

    def test_encode_decode_roundtrip(self):
        offset = 42
        cursor = encode_cursor(offset)
        assert decode_cursor(cursor) == offset

    def test_decode_invalid_returns_zero(self):
        assert decode_cursor("invalid") == 0
        assert decode_cursor("") == 0


class TestPaginate:
    """Test paginate function."""

    def test_first_page_with_more(self):
        items = list(range(15))
        page = paginate(items, limit=10, cursor=None, total=100)

        assert len(page.items) == 10
        assert page.page_info.has_next is True
        assert page.page_info.has_prev is False
        assert page.page_info.next_cursor is not None
        assert page.page_info.total == 100

    def test_last_page(self):
        items = list(range(5))
        cursor = encode_cursor(90)
        page = paginate(items, limit=10, cursor=cursor, total=95)

        assert len(page.items) == 5
        assert page.page_info.has_next is False
        assert page.page_info.has_prev is True

    def test_empty_page(self):
        page = paginate([], limit=10, cursor=None)

        assert len(page.items) == 0
        assert page.page_info.has_next is False
        assert page.page_info.has_prev is False
