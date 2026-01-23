"""
Name: RQ Worker Entrypoint

Responsibilities:
  - Start RQ worker for document processing jobs
"""

import os

from redis import Redis
from rq import Worker

from ..platform.config import get_settings
from ..platform.logger import logger
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
