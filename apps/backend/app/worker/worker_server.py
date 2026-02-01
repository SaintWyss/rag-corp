"""
===============================================================================
TARJETA CRC — worker/worker_server.py (HTTP liviano para Worker)
===============================================================================

Responsabilidades:
  - Exponer endpoints operativos del worker:
      * GET /healthz  (liveness)
      * GET /readyz   (readiness: Redis + DB)
      * GET /metrics  (Prometheus; opcionalmente protegido)
  - Implementar autorización de /metrics:
      - API Key con scope "metrics" (keys_config)
      - o permiso RBAC ADMIN_METRICS (rbac_config)
  - Evitar loguear secretos (API keys).

Patrones aplicados:
  - Minimal HTTP Server: http.server (bajo overhead, sin FastAPI extra).
  - Policy Gate: autorización explícita para métricas.
  - Best-effort: si el server no puede iniciar, no rompe el worker.

Colaboradores:
  - worker_health.health_payload / readiness_payload
  - crosscutting.metrics.get_metrics_response
  - identity.auth.APIKeyValidator / get_keys_config
  - identity.rbac.get_rbac_config / Permission
===============================================================================
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from ..crosscutting.config import get_settings
from ..crosscutting.logger import logger
from ..crosscutting.metrics import get_metrics_response
from ..identity.auth import APIKeyValidator, _hash_key, get_keys_config
from ..identity.rbac import Permission, get_rbac_config
from .worker_health import health_payload, readiness_payload


class _WorkerHandler(BaseHTTPRequestHandler):
    """Handler HTTP minimalista para endpoints operativos del worker."""

    def _metrics_authorized(self) -> tuple[bool, int]:
        """
        Autoriza /metrics.
        Retorna (allowed, http_status).
        """
        settings = get_settings()
        if not settings.metrics_require_auth:
            return True, 200

        api_key = (self.headers.get("X-API-Key") or "").strip()
        if not api_key:
            return False, 401

        keys_config = get_keys_config()
        rbac_config = get_rbac_config()

        # Si no hay ninguna configuración, denegamos (fail-safe).
        if not keys_config and not rbac_config:
            return False, 403

        # 1) API Keys config (scope "metrics")
        if keys_config:
            validator = APIKeyValidator(keys_config)
            if validator.validate_key(api_key) and validator.validate_scope(
                api_key, "metrics"
            ):
                return True, 200

        # 2) RBAC config por hash de key (permiso ADMIN_METRICS)
        if rbac_config:
            key_hash = _hash_key(api_key)
            if rbac_config.check_permission(key_hash, Permission.ADMIN_METRICS):
                return True, 200

        return False, 403

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/healthz":
            self._write_json(200, health_payload())
            return

        if path == "/readyz":
            payload = readiness_payload()
            status = 200 if payload.get("ok") else 503
            self._write_json(status, payload)
            return

        if path == "/metrics":
            allowed, status = self._metrics_authorized()
            if not allowed:
                self._write_json(status, {"detail": "Acceso denegado para métricas"})
                return

            body, content_type = get_metrics_response()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        """
        Reemplaza el logging default del server por logger estructurado.
        """
        logger.info(
            "Worker HTTP request",
            extra={
                "client": self.client_address[0] if self.client_address else None,
                "path": getattr(self, "path", None),
            },
        )

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_worker_http_server(port: int) -> ThreadingHTTPServer | None:
    """
    Inicia el HTTP server en un thread daemon.

    Retorna:
      - server si inició bien
      - None si falló (best-effort)
    """
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), _WorkerHandler)
    except OSError as exc:
        logger.warning("Worker HTTP server no pudo iniciar", extra={"error": str(exc)})
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Worker HTTP server iniciado", extra={"port": port})
    return server


__all__ = ["start_worker_http_server"]
