"""
Name: List Documents Use Case Tests

Responsibilities:
  - Verify pagination and filter wiring for list documents
"""

from uuid import uuid4

import pytest

from app.application.use_cases.list_documents import ListDocumentsUseCase
from app.domain.entities import Document
from app.pagination import encode_cursor


pytestmark = pytest.mark.unit


def _doc(title: str) -> Document:
    return Document(id=uuid4(), title=title)


def test_list_documents_paginates_with_cursor(mock_repository):
    docs = [_doc("One"), _doc("Two"), _doc("Three")]
    mock_repository.list_documents.return_value = docs

    use_case = ListDocumentsUseCase(repository=mock_repository)

    cursor = encode_cursor(20)
    result = use_case.execute(
        limit=2,
        cursor=cursor,
        query="manual",
        status="READY",
        tag="sales",
        sort="created_at_desc",
    )

    mock_repository.list_documents.assert_called_once_with(
        limit=3,
        offset=20,
        query="manual",
        status="READY",
        tag="sales",
        sort="created_at_desc",
    )
    assert len(result.documents) == 2
    assert result.next_cursor == encode_cursor(22)


def test_list_documents_no_next_cursor(mock_repository):
    docs = [_doc("One"), _doc("Two")]
    mock_repository.list_documents.return_value = docs

    use_case = ListDocumentsUseCase(repository=mock_repository)
    result = use_case.execute(limit=2, offset=0)

    mock_repository.list_documents.assert_called_once_with(
        limit=3,
        offset=0,
        query=None,
        status=None,
        tag=None,
        sort=None,
    )
    assert len(result.documents) == 2
    assert result.next_cursor is None
