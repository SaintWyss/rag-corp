"""
Name: Worker Health Checks

Responsibilities:
  - Check Redis and Postgres connectivity for worker readiness
  - Provide a CLI entrypoint for container healthchecks
"""

from __future__ import annotations

import json
import time
from typing import Any

import psycopg
from redis import Redis

from ..crosscutting.config import get_settings
from ..crosscutting.logger import logger

_START_TIME = time.time()


def _check_db(database_url: str) -> bool:
    try:
        with psycopg.connect(database_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as exc:
        logger.warning("Worker readiness: DB unavailable", extra={"error": str(exc)})
        return False


def _check_redis(redis_url: str) -> bool:
    try:
        redis = Redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return bool(redis.ping())
    except Exception as exc:
        logger.warning("Worker readiness: Redis unavailable", extra={"error": str(exc)})
        return False


def readiness_payload() -> dict[str, Any]:
    settings = get_settings()
    db_ok = _check_db(settings.database_url)
    redis_ok = _check_redis(settings.redis_url or "")

    return {
        "ok": db_ok and redis_ok,
        "db": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }


def health_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "uptime_seconds": int(time.time() - _START_TIME),
    }


def main() -> None:
    payload = readiness_payload()
    print(json.dumps(payload))
    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
