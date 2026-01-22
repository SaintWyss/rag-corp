"""
Name: Worker HTTP Server

Responsibilities:
  - Expose /healthz, /readyz, /metrics for worker process
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .logger import logger
from .auth import APIKeyValidator, get_keys_config, _hash_key
from .config import get_settings
from .metrics import get_metrics_response
from .rbac import Permission, get_rbac_config
from .worker_health import health_payload, readiness_payload


class _WorkerHandler(BaseHTTPRequestHandler):
    def _metrics_authorized(self) -> tuple[bool, int]:
        settings = get_settings()
        if not settings.metrics_require_auth:
            return True, 200

        api_key = self.headers.get("X-API-Key")
        if not api_key:
            return False, 401

        keys_config = get_keys_config()
        rbac_config = get_rbac_config()

        if not keys_config and not rbac_config:
            return False, 403

        if keys_config:
            validator = APIKeyValidator(keys_config)
            if validator.validate_key(api_key) and validator.validate_scope(
                api_key, "metrics"
            ):
                return True, 200

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
            status = 200 if payload["ok"] else 503
            self._write_json(status, payload)
            return

        if path == "/metrics":
            allowed, status = self._metrics_authorized()
            if not allowed:
                self._write_json(status, {"detail": "Metrics access denied"})
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
        logger.info(
            "Worker HTTP request",
            extra={
                "client": self.client_address[0] if self.client_address else None,
                "path": self.path,
            },
        )

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_worker_http_server(port: int) -> ThreadingHTTPServer | None:
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), _WorkerHandler)
    except OSError as exc:
        logger.warning("Worker HTTP server failed to start", extra={"error": str(exc)})
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Worker HTTP server started", extra={"port": port})
    return server
