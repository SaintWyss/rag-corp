"""
Name: Document File Metadata Tests

Responsibilities:
  - Ensure repository updates file metadata without external services
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.repositories.postgres.document import (
    PostgresDocumentRepository,
)


pytestmark = pytest.mark.unit


def test_update_document_file_metadata_executes_update():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_conn.execute.return_value = mock_result
    mock_pool.connection.return_value.__enter__.return_value = mock_conn

    repo = PostgresDocumentRepository(pool=mock_pool)
    doc_id = uuid4()

    updated = repo.update_document_file_metadata(
        doc_id,
        workspace_id=uuid4(),
        file_name="doc.pdf",
        mime_type="application/pdf",
        storage_key="documents/doc.pdf",
        uploaded_by_user_id=uuid4(),
        status="PENDING",
        error_message=None,
    )

    assert updated is True
    mock_conn.execute.assert_called_once()
