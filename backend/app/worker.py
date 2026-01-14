"""
Name: RQ Worker Entrypoint

Responsibilities:
  - Start RQ worker for document processing jobs
"""

import os
from redis import Redis
from rq import Connection, Worker

from .config import get_settings


def main() -> None:
    settings = get_settings()
    redis_url = settings.redis_url or os.getenv("REDIS_URL", "")
    if not redis_url:
        raise SystemExit("REDIS_URL is required to run the worker")

    queue_name = os.getenv("DOCUMENT_QUEUE_NAME", "documents")

    redis_conn = Redis.from_url(redis_url)
    with Connection(redis_conn):
        worker = Worker([queue_name])
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
