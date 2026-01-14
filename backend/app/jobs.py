"""
Name: Background Job Definitions

Responsibilities:
  - Entry points for RQ jobs
"""

import logging
from uuid import UUID

from .application.use_cases import (
    ProcessUploadedDocumentInput,
    ProcessUploadedDocumentUseCase,
)
from .container import (
    get_document_repository,
    get_document_text_extractor,
    get_embedding_service,
    get_file_storage,
    get_text_chunker,
)


logger = logging.getLogger(__name__)


def process_document_job(document_id: str) -> None:
    """R: RQ job to process a single uploaded document."""
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        logger.error("Invalid document_id for job", extra={"document_id": document_id})
        return

    use_case = ProcessUploadedDocumentUseCase(
        repository=get_document_repository(),
        storage=get_file_storage(),
        extractor=get_document_text_extractor(),
        chunker=get_text_chunker(),
        embedding_service=get_embedding_service(),
    )
    use_case.execute(ProcessUploadedDocumentInput(document_id=doc_uuid))
