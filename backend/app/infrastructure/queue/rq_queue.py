"""
Name: RQ Document Processing Queue

Responsibilities:
  - Enqueue background jobs to Redis using RQ
"""

from uuid import UUID

from redis import Redis
from rq import Queue, Retry

from ...domain.services import DocumentProcessingQueue


class RQDocumentProcessingQueue(DocumentProcessingQueue):
    """R: Enqueue document processing jobs on Redis."""

    def __init__(
        self,
        redis_url: str,
        queue_name: str = "documents",
        retry_max_attempts: int = 3,
        retry_intervals: list[int] | None = None,
    ):
        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(queue_name, connection=self._redis)
        self._retry = Retry(
            max=retry_max_attempts,
            interval=retry_intervals,
        )

    def enqueue_document_processing(self, document_id: UUID) -> str:
        job = self._queue.enqueue(
            "app.jobs.process_document_job",
            str(document_id),
            retry=self._retry,
        )
        return job.id
