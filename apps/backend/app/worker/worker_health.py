"""
===============================================================================
TARJETA CRC — worker/worker_health.py (Health & Readiness del Worker)
===============================================================================

Responsabilidades:
  - Verificar conectividad de Redis y Postgres para readiness del worker.
  - Entregar payloads simples para /readyz y /healthz.
  - Exponer CLI de healthcheck para contenedores (exit code 0/1).

Patrones aplicados:
  - Fail-safe diagnostics: nunca lanzar excepciones al caller; devolver estado.
  - Timeouts agresivos: healthchecks deben responder rápido.

Colaboradores:
  - crosscutting.config.get_settings
  - redis.Redis
  - psycopg (conexión directa para check rápido)
===============================================================================
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
    """Chequea DB con timeout corto."""
    if not database_url:
        return False
    try:
        with psycopg.connect(database_url, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as exc:
        logger.warning("Readiness worker: DB no disponible", extra={"error": str(exc)})
        return False


def _check_redis(redis_url: str) -> bool:
    """Chequea Redis con timeout corto."""
    if not redis_url:
        return False
    try:
        redis = Redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
        return bool(redis.ping())
    except Exception as exc:
        logger.warning(
            "Readiness worker: Redis no disponible", extra={"error": str(exc)}
        )
        return False


def readiness_payload() -> dict[str, Any]:
    """
    Readiness:
      - ok si Redis y DB están conectados.
    """
    settings = get_settings()
    db_ok = _check_db(settings.database_url)
    redis_ok = _check_redis(settings.redis_url or "")

    return {
        "ok": bool(db_ok and redis_ok),
        "db": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }


def health_payload() -> dict[str, Any]:
    """
    Health:
      - proceso vivo (no valida dependencias).
    """
    return {
        "ok": True,
        "uptime_seconds": int(time.time() - _START_TIME),
    }


def main() -> None:
    """
    CLI healthcheck:
      - imprime readiness payload
      - exit 0 si ok, 1 si no
    """
    payload = readiness_payload()
    print(json.dumps(payload))
    raise SystemExit(0 if payload.get("ok") else 1)


if __name__ == "__main__":
    main()
