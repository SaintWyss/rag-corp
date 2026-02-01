"""
===============================================================================
TARJETA CRC — worker/worker.py (Entrypoint del proceso Worker)
===============================================================================

Responsabilidades:
  - Levantar un proceso RQ Worker consumiendo una cola (documents por defecto).
  - Inicializar dependencias del proceso: Redis + pool de BD.
  - Exponer HTTP liviano de health/ready/metrics para orquestadores.
  - Apagar recursos de forma segura y consistente.

Patrones aplicados:
  - Process Bootstrap: inicializa recursos del proceso antes de trabajar.
  - Fail-fast: si Redis/BD no están disponibles al inicio, no arrancar “a medias”.
  - Best-effort health server: si el puerto está ocupado, log y continuar.

Colaboradores:
  - crosscutting.config.get_settings
  - infrastructure.db.pool.init_pool / close_pool
  - redis.Redis + rq.Worker
  - worker_server.start_worker_http_server
===============================================================================
"""

from __future__ import annotations

import os

from redis import Redis
from rq import Queue, Worker

from ..crosscutting.config import get_settings
from ..crosscutting.logger import logger
from ..infrastructure.db.pool import close_pool, init_pool
from .worker_server import start_worker_http_server


def _get_env_int(name: str, default: int) -> int:
    """Lee un entero desde env con fallback seguro."""
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except Exception:
        return default


def _build_redis_connection(redis_url: str) -> Redis:
    """
    Crea conexión Redis con timeouts razonables para worker.

    Nota:
      - No queremos bloqueos largos en pings o socket timeouts.
    """
    return Redis.from_url(
        redis_url,
        socket_connect_timeout=2,
        socket_timeout=5,
        health_check_interval=30,
    )


def main() -> None:
    settings = get_settings()

    redis_url = (settings.redis_url or os.getenv("REDIS_URL", "")).strip()
    if not redis_url:
        raise SystemExit("REDIS_URL es requerido para ejecutar el worker.")

    queue_name = os.getenv("DOCUMENT_QUEUE_NAME", "documents").strip() or "documents"
    http_port = _get_env_int("WORKER_HTTP_PORT", 8001)

    # R: Redis (fail-fast si no responde).
    redis_conn = _build_redis_connection(redis_url)
    try:
        redis_conn.ping()
    except Exception as exc:
        logger.error("Redis no disponible para worker", extra={"error": str(exc)})
        raise SystemExit("Redis no disponible.")

    # R: Pool DB (fail-fast si no inicializa).
    init_pool(
        database_url=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )

    server = None
    try:
        # R: HTTP server liviano (best-effort).
        server = start_worker_http_server(http_port)

        logger.info(
            "Worker arrancando",
            extra={
                "queue": queue_name,
                "http_port": http_port,
                "redis_configured": True,
                "db_pool_min": settings.db_pool_min_size,
                "db_pool_max": settings.db_pool_max_size,
            },
        )

        queue = Queue(name=queue_name, connection=redis_conn)
        worker = Worker([queue], connection=redis_conn)

        # R: Loop principal del worker.
        worker.work(with_scheduler=False)

    except KeyboardInterrupt:
        logger.info("Worker detenido por señal (KeyboardInterrupt)")
    finally:
        # R: Cierre ordenado.
        try:
            if server is not None:
                server.shutdown()
                server.server_close()
        except Exception:
            # Best-effort: nunca bloquear shutdown por el server.
            pass

        close_pool()
        logger.info("Worker apagado")


if __name__ == "__main__":
    main()
