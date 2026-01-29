"""
Name: RQ Document Processing Queue

Responsibilities:
  - Enqueue document processing jobs onto Redis via RQ
  - Construct the queue connection using the configured Redis URL
  - Apply retry policy settings for background job resilience
  - Provide job identifiers back to the caller
  - Keep queue wiring aligned with worker configuration

Collaborators:
  - redis.Redis: Redis connection client
  - rq.Queue: queue abstraction for enqueuing jobs
  - rq.Retry: retry policy configuration
  - domain.services.DocumentProcessingQueue: port/interface contract
  - app.jobs.process_document_job: job entrypoint name (string)

Notes/Constraints:
  - Job name is referenced by string and must remain stable
  - Queue name defaults to "documents" unless overridden
  - Retry settings are applied per enqueue call
  - UUIDs are converted to strings for job arguments
  - This adapter performs no payload validation beyond types
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

    def enqueue_document_processing(
        self, document_id: UUID, *, workspace_id: UUID
    ) -> str:
        job = self._queue.enqueue(
            "app.jobs.process_document_job",
            str(document_id),
            str(workspace_id),
            retry=self._retry,
        )
        return job.id
