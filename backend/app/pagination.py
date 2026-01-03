"""
Name: Pagination Utilities

Responsibilities:
  - Provide cursor-based pagination for list endpoints
  - Standardized page response model
"""

from __future__ import annotations

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
import base64


T = TypeVar("T")


class PageInfo(BaseModel):
    """Pagination metadata."""

    has_next: bool = Field(description="Whether there are more items after this page")
    has_prev: bool = Field(description="Whether there are items before this page")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    prev_cursor: Optional[str] = Field(None, description="Cursor for previous page")
    total: Optional[int] = Field(None, description="Total count (if available)")


class Page(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: List[T] = Field(description="Items in current page")
    page_info: PageInfo = Field(description="Pagination metadata")


def encode_cursor(offset: int) -> str:
    """Encode offset as base64 cursor."""
    return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode()


def decode_cursor(cursor: str) -> int:
    """Decode cursor to offset."""
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        if decoded.startswith("offset:"):
            return int(decoded[7:])
    except Exception:
        pass
    return 0


def paginate(
    items: List[T],
    limit: int,
    cursor: Optional[str] = None,
    total: Optional[int] = None,
) -> Page[T]:
    """
    Create paginated response from items list.
    
    Args:
        items: Full or page-sized list of items
        limit: Page size
        cursor: Current cursor (if any)
        total: Total count (optional)
    
    Returns:
        Page with items and pagination metadata
    """
    offset = decode_cursor(cursor) if cursor else 0
    
    has_next = len(items) > limit
    page_items = items[:limit]
    
    return Page(
        items=page_items,
        page_info=PageInfo(
            has_next=has_next,
            has_prev=offset > 0,
            next_cursor=encode_cursor(offset + limit) if has_next else None,
            prev_cursor=encode_cursor(max(0, offset - limit)) if offset > 0 else None,
            total=total,
        ),
    )
