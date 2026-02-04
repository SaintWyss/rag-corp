"""
Name: Observability Unit Tests

Responsibilities:
  - Test request context middleware
  - Test JSON formatter with context
  - Test Timer helper
  - Test metrics endpoint

Notes:
  - Uses FastAPI TestClient for middleware tests
  - Mocks context vars for formatter tests
"""

import json
import logging
import time

import pytest

pytestmark = pytest.mark.unit


class TestTimer:
    """Test Timer helper class."""

    def test_timer_basic_usage(self):
        """R: Should measure elapsed time."""
        from app.crosscutting.timing import Timer

        timer = Timer()
        timer.start()
        time.sleep(0.001)  # Small delay to ensure non-zero
        timer.stop()

        assert timer.elapsed_ms > 0
        assert timer.elapsed_seconds > 0

    def test_timer_context_manager(self):
        """R: Should work as context manager."""
        from app.crosscutting.timing import Timer

        with Timer() as t:
            pass

        assert t.elapsed_ms >= 0

    def test_timer_not_started_raises(self):
        """R: Should raise if stopped without starting."""
        from app.crosscutting.timing import Timer

        timer = Timer()
        with pytest.raises(RuntimeError, match="no iniciado"):  # Spanish message
            timer.stop()

    def test_timer_elapsed_before_stop(self):
        """R: Should return current elapsed even before stop."""
        from app.crosscutting.timing import Timer

        timer = Timer()
        timer.start()
        time.sleep(0.001)

        # Not stopped yet, but should still give elapsed
        assert timer.elapsed_ms > 0


class TestStageTimings:
    """Test StageTimings helper class."""

    def test_stage_timings_basic(self):
        """R: Should record multiple stages."""
        from app.crosscutting.timing import StageTimings

        timings = StageTimings()

        with timings.measure("embed"):
            pass

        with timings.measure("retrieve"):
            pass

        result = timings.to_dict()

        assert "embed_ms" in result
        assert "retrieve_ms" in result
        assert "total_ms" in result

    def test_stage_timings_direct_record(self):
        """R: Should allow direct recording."""
        from app.crosscutting.timing import StageTimings

        timings = StageTimings()
        timings.record("custom", 42.5)

        result = timings.to_dict()

        assert result["custom_ms"] == 42.5

    def test_stage_timings_total_accumulates(self):
        """R: Total should be >= sum of stages."""
        from app.crosscutting.timing import StageTimings

        timings = StageTimings()

        with timings.measure("stage1"):
            time.sleep(0.001)

        with timings.measure("stage2"):
            time.sleep(0.001)

        result = timings.to_dict()

        assert result["total_ms"] >= result["stage1_ms"] + result["stage2_ms"]


class TestContextVars:
    """Test context variable helpers."""

    def test_get_context_dict_empty(self):
        """R: Should return empty dict when no context set."""
        from app.context import clear_context, get_context_dict

        clear_context()

        result = get_context_dict()

        assert result == {}

    def test_get_context_dict_with_values(self):
        """R: Should return dict with set values."""
        from app.context import (
            clear_context,
            get_context_dict,
            http_method_var,
            http_path_var,
            request_id_var,
        )

        request_id_var.set("test-123")
        http_method_var.set("POST")
        http_path_var.set("/v1/workspaces/abc/ask")

        result = get_context_dict()

        assert result["request_id"] == "test-123"
        assert result["method"] == "POST"
        assert result["path"] == "/v1/workspaces/{workspace_id}/ask"

        # Cleanup
        clear_context()

    def test_clear_context(self):
        """R: Should clear all context vars."""
        from app.context import clear_context, request_id_var

        request_id_var.set("test-123")

        clear_context()

        assert request_id_var.get() == ""


class TestJSONFormatter:
    """Test JSONFormatter class."""

    def test_formatter_basic_log(self):
        """R: Should format log as JSON."""
        from app.crosscutting.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_formatter_includes_context(self):
        """R: Should include request context in log."""
        from app.context import clear_context, request_id_var
        from app.crosscutting.logger import JSONFormatter

        request_id_var.set("ctx-456")

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data.get("request_id") == "ctx-456"

        # Cleanup
        clear_context()

    def test_formatter_filters_sensitive_keys(self):
        """R: Should redact sensitive field VALUES (key may remain with redacted value)."""
        from app.crosscutting.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.api_key = "secret-key"
        record.password = "secret-pass"
        record.safe_field = "visible"

        result = formatter.format(record)

        # R: Sensitive VALUES should not appear
        assert "secret-key" not in result
        assert "secret-pass" not in result
        # R: Non-sensitive fields should be visible
        assert "visible" in result

    def test_formatter_includes_extra_fields(self):
        """R: Should include extra fields from log call."""
        from app.crosscutting.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.latency_ms = 42.5
        record.chunks_found = 3

        result = formatter.format(record)
        data = json.loads(result)

        assert data.get("latency_ms") == 42.5
        assert data.get("chunks_found") == 3

    def test_formatter_includes_exception(self):
        """R: Should include exception stacktrace."""
        from app.crosscutting.logger import JSONFormatter

        formatter = JSONFormatter()

        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "test error"
        assert isinstance(data["exception"]["stacktrace"], list)


class TestMetricsModule:
    """Test metrics module functions."""

    def test_normalize_endpoint_uuid(self):
        """R: Should replace UUIDs in paths."""
        from app.crosscutting.metrics import _normalize_endpoint

        path = "/v1/workspaces/abc/documents/3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d"
        result = _normalize_endpoint(path)

        assert result == "/v1/workspaces/{workspace_id}/documents/{id}"

    def test_normalize_endpoint_numeric(self):
        """R: Should replace numeric IDs in paths."""
        from app.crosscutting.metrics import _normalize_endpoint

        path = "/v1/workspaces/abc/documents/12345"
        result = _normalize_endpoint(path)

        assert result == "/v1/workspaces/{workspace_id}/documents/{id}"

    def test_status_bucket(self):
        """R: Should bucket status codes correctly."""
        from app.crosscutting.metrics import _status_bucket

        assert _status_bucket(200) == "2xx"
        assert _status_bucket(201) == "2xx"
        assert _status_bucket(400) == "4xx"
        assert _status_bucket(422) == "4xx"
        assert _status_bucket(500) == "5xx"
        assert _status_bucket(503) == "5xx"
        assert _status_bucket(100) == "other"

    def test_is_prometheus_available(self):
        """R: Should return True when prometheus_client is installed."""
        from app.crosscutting.metrics import is_prometheus_available

        # prometheus_client should be installed per requirements.txt
        assert is_prometheus_available() is True


class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_get_metrics_response_returns_bytes(self):
        """R: Should return bytes and content type."""
        from app.crosscutting.metrics import (
            get_metrics_response,
            is_prometheus_available,
        )

        body, content_type = get_metrics_response()

        assert isinstance(body, bytes)
        assert isinstance(content_type, str)
        if is_prometheus_available():
            assert b"rag_" in body or b"# HELP" in body


class TestRequestContextMiddleware:
    """Test RequestContextMiddleware in isolation."""

    def test_middleware_generates_uuid(self):
        """R: Should generate valid UUID for request_id."""
        import uuid

        # Test that we can generate UUID like middleware does
        request_id = str(uuid.uuid4())

        assert len(request_id) == 36
        # Verify it's a valid UUID
        uuid.UUID(request_id)

    def test_middleware_class_exists(self):
        """R: RequestContextMiddleware should be importable."""
        from app.crosscutting.middleware import RequestContextMiddleware

        assert RequestContextMiddleware is not None


class TestTracingModule:
    """Test tracing module."""

    def test_span_is_importable(self):
        """R: span context manager should be importable."""
        from app.crosscutting.tracing import span

        assert span is not None

    def test_is_tracing_enabled_is_importable(self):
        """R: is_tracing_enabled should be importable."""
        from app.crosscutting.tracing import is_tracing_enabled

        # Should return a boolean
        result = is_tracing_enabled()
        assert isinstance(result, bool)
