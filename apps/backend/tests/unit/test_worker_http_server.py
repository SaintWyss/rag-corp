import http.client
import json

from app.worker import worker_server


def _request(port: int, path: str) -> tuple[int, bytes, dict[str, str]]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    conn.request("GET", path)
    res = conn.getresponse()
    body = res.read()
    headers = {k: v for k, v in res.getheaders()}
    conn.close()
    return res.status, body, headers


def _start_server(monkeypatch):
    monkeypatch.setattr(
        worker_server,
        "health_payload",
        lambda: {"ok": True, "uptime_seconds": 1},
    )
    monkeypatch.setattr(
        worker_server,
        "readiness_payload",
        lambda: {"ok": True, "db": "connected", "redis": "connected"},
    )
    server = worker_server.start_worker_http_server(0)
    assert server is not None
    return server, server.server_address[1]


def test_worker_healthz(monkeypatch) -> None:
    server, port = _start_server(monkeypatch)
    try:
        status, body, _ = _request(port, "/healthz")
        assert status == 200
        payload = json.loads(body)
        assert payload["ok"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_worker_readyz(monkeypatch) -> None:
    server, port = _start_server(monkeypatch)
    try:
        status, body, _ = _request(port, "/readyz")
        assert status == 200
        payload = json.loads(body)
        assert payload["ok"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_worker_metrics(monkeypatch) -> None:
    server, port = _start_server(monkeypatch)
    try:
        status, body, headers = _request(port, "/metrics")
        assert status == 200
        assert headers.get("Content-Type")
        assert b"rag_requests_total" in body
    finally:
        server.shutdown()
        server.server_close()
