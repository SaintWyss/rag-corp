"""
Name: Background Job Definitions

Responsibilities:
  - Entry points for RQ jobs
"""

import time
from uuid import UUID

from rq import get_current_job

from .application.use_cases import (
    ProcessUploadedDocumentInput,
    ProcessUploadedDocumentUseCase,
)
from .context import clear_context, request_id_var
from .container import (
    get_document_repository,
    get_document_text_extractor,
    get_embedding_service,
    get_file_storage,
    get_text_chunker,
)
from .logger import logger
from .metrics import (
    observe_worker_duration,
    record_worker_failed,
    record_worker_processed,
)
from .tracing import span


def process_document_job(document_id: str) -> None:
    """R: RQ job to process a single uploaded document."""
    job = get_current_job()
    job_id = job.id if job else None
    request_id_var.set(job_id or document_id)
    start_time = time.perf_counter()
    status = "UNKNOWN"

    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        status = "INVALID"
        logger.error(
            "Invalid document_id for job",
            extra={"document_id": document_id, "job_id": job_id},
        )
        record_worker_processed(status)
        record_worker_failed()
        observe_worker_duration(time.perf_counter() - start_time)
        clear_context()
        return

    use_case = ProcessUploadedDocumentUseCase(
        repository=get_document_repository(),
        storage=get_file_storage(),
        extractor=get_document_text_extractor(),
        chunker=get_text_chunker(),
        embedding_service=get_embedding_service(),
    )
    logger.info(
        "Worker job started",
        extra={"document_id": str(doc_uuid), "job_id": job_id},
    )
    try:
        with span(
            "worker.process_document",
            {"document_id": str(doc_uuid), "job_id": job_id or ""},
        ):
            result = use_case.execute(
                ProcessUploadedDocumentInput(document_id=doc_uuid)
            )
        status = result.status
    except Exception:
        status = "FAILED"
        logger.exception(
            "Worker job crashed",
            extra={"document_id": str(doc_uuid), "job_id": job_id},
        )
        raise
    finally:
        duration = time.perf_counter() - start_time
        record_worker_processed(status)
        if status == "FAILED":
            record_worker_failed()
        observe_worker_duration(duration)
        logger.info(
            "Worker job finished",
            extra={
                "document_id": str(doc_uuid),
                "job_id": job_id,
                "status": status,
                "duration_seconds": round(duration, 3),
            },
        )
        clear_context()
