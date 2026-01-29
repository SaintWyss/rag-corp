"""
Name: RQ Worker Entrypoint

Responsibilities:
  - Start an RQ worker process for document processing jobs
  - Initialize Redis connection and validate required environment
  - Initialize and close the Postgres connection pool for jobs
  - Start the worker health HTTP server for liveness checks
  - Emit structured startup/shutdown logs for observability

Collaborators:
  - redis.Redis: connection to the queue backend
  - rq.Worker: job runner for the documents queue
  - worker_server.start_worker_http_server: health endpoint process
  - crosscutting.config.get_settings: runtime configuration access
  - infrastructure.db.pool: init_pool/close_pool lifecycle helpers
  - crosscutting.logger: structured logging

Notes/Constraints:
  - REDIS_URL must be set; missing config exits the process
  - DOCUMENT_QUEUE_NAME and WORKER_HTTP_PORT control runtime wiring
  - Worker uses with_scheduler=False to avoid cron/scheduler jobs
  - Pool must close on shutdown to prevent resource leakage
"""

import os

from redis import Redis
from rq import Worker

from ..crosscutting.config import get_settings
from ..crosscutting.logger import logger
from .worker_server import start_worker_http_server
from ..infrastructure.db.pool import init_pool, close_pool


def main() -> None:
    settings = get_settings()
    redis_url = settings.redis_url or os.getenv("REDIS_URL", "")
    if not redis_url:
        raise SystemExit("REDIS_URL is required to run the worker")

    queue_name = os.getenv("DOCUMENT_QUEUE_NAME", "documents")
    http_port = int(os.getenv("WORKER_HTTP_PORT", "8001"))

    redis_conn = Redis.from_url(redis_url)
    init_pool(
        database_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    start_worker_http_server(http_port)

    logger.info(
        "Worker starting",
        extra={
            "queue": queue_name,
            "redis_url": redis_url,
            "http_port": http_port,
        },
    )
    worker = Worker([queue_name], connection=redis_conn)
    try:
        worker.work(with_scheduler=False)
    finally:
        close_pool()
        logger.info("Worker shutdown")


if __name__ == "__main__":
    main()
