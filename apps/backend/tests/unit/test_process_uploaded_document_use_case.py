"""
Name: Process Uploaded Document Use Case Tests

Responsibilities:
  - Validate status transitions and persistence calls
  - Ensure parsing/embedding flow uses injected services
"""

from uuid import uuid4
from unittest.mock import MagicMock

import pytest

from app.application.use_cases import (
    ProcessUploadedDocumentInput,
    ProcessUploadedDocumentUseCase,
)
from app.domain.entities import Document


pytestmark = pytest.mark.unit


def _document(status: str | None = "PENDING") -> Document:
    return Document(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Doc",
        source=None,
        metadata={},
        file_name="file.pdf",
        mime_type="application/pdf",
        storage_key="documents/1/file.pdf",
        uploaded_by_user_id=None,
        status=status,
    )


def test_process_document_happy_path():
    repo = MagicMock()
    storage = MagicMock()
    extractor = MagicMock()
    chunker = MagicMock()
    embedding_service = MagicMock()

    doc = _document("PENDING")
    repo.get_document.return_value = doc
    repo.transition_document_status.side_effect = [True, True]
    storage.download_file.return_value = b"data"
    extractor.extract_text.return_value = "hello world"
    chunker.chunk.return_value = ["hello", "world"]
    embedding_service.embed_batch.return_value = [[0.1] * 768, [0.2] * 768]

    use_case = ProcessUploadedDocumentUseCase(
        repository=repo,
        storage=storage,
        extractor=extractor,
        chunker=chunker,
        embedding_service=embedding_service,
    )

    result = use_case.execute(
        ProcessUploadedDocumentInput(
            document_id=doc.id,
            workspace_id=doc.workspace_id,
        )
    )

    assert result.status == "READY"
    assert result.chunks_created == 2
    storage.download_file.assert_called_once_with(doc.storage_key)
    extractor.extract_text.assert_called_once()
    chunker.chunk.assert_called_once_with("hello world")
    embedding_service.embed_batch.assert_called_once_with(["hello", "world"])
    repo.delete_chunks_for_document.assert_called_once_with(
        doc.id, workspace_id=doc.workspace_id
    )
    repo.save_chunks.assert_called_once()


def test_process_document_skips_ready():
    repo = MagicMock()
    storage = MagicMock()
    extractor = MagicMock()
    chunker = MagicMock()
    embedding_service = MagicMock()

    doc = _document("READY")
    repo.get_document.return_value = doc

    use_case = ProcessUploadedDocumentUseCase(
        repository=repo,
        storage=storage,
        extractor=extractor,
        chunker=chunker,
        embedding_service=embedding_service,
    )

    result = use_case.execute(
        ProcessUploadedDocumentInput(
            document_id=doc.id,
            workspace_id=doc.workspace_id,
        )
    )

    assert result.status == "READY"
    repo.transition_document_status.assert_not_called()
    storage.download_file.assert_not_called()


def test_process_document_sets_failed_on_error():
    repo = MagicMock()
    storage = MagicMock()
    extractor = MagicMock()
    chunker = MagicMock()
    embedding_service = MagicMock()

    doc = _document("PENDING")
    repo.get_document.return_value = doc
    repo.transition_document_status.side_effect = [True, True]
    storage.download_file.return_value = b"data"
    extractor.extract_text.side_effect = RuntimeError("boom")

    use_case = ProcessUploadedDocumentUseCase(
        repository=repo,
        storage=storage,
        extractor=extractor,
        chunker=chunker,
        embedding_service=embedding_service,
    )

    result = use_case.execute(
        ProcessUploadedDocumentInput(
            document_id=doc.id,
            workspace_id=doc.workspace_id,
        )
    )

    assert result.status == "FAILED"
    calls = repo.transition_document_status.call_args_list
    assert calls[-1].kwargs["to_status"] == "FAILED"
