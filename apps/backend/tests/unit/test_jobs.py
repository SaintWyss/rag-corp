"""
Name: Background Job Tests

Responsibilities:
  - Validate job wiring calls the processing use case
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.worker.jobs import process_document_job


pytestmark = pytest.mark.unit


def test_process_document_job_invokes_use_case():
    doc_id = uuid4()
    workspace_id = uuid4()
    mock_use_case = MagicMock()

    with patch("app.worker.jobs.get_document_repository", return_value=MagicMock()):
        with patch("app.worker.jobs.get_file_storage", return_value=MagicMock()):
            with patch(
                "app.worker.jobs.get_document_text_extractor", return_value=MagicMock()
            ):
                with patch(
                    "app.worker.jobs.get_text_chunker", return_value=MagicMock()
                ):
                    with patch(
                        "app.worker.jobs.get_embedding_service",
                        return_value=MagicMock(),
                    ):
                        with patch(
                            "app.worker.jobs.ProcessUploadedDocumentUseCase",
                            return_value=mock_use_case,
                        ):
                            process_document_job(
                                str(doc_id),
                                str(workspace_id),
                            )

    assert mock_use_case.execute.call_count == 1
    input_arg = mock_use_case.execute.call_args.args[0]
    assert input_arg.document_id == doc_id
    assert input_arg.workspace_id == workspace_id
