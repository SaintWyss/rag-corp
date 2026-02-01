"""Unit tests for error_responses module."""

from app.crosscutting.error_responses import (
    ErrorCode,
    ErrorDetail,
    database_error,
    forbidden,
    internal_error,
    llm_error,
    not_found,
    rate_limited,
    unauthorized,
    validation_error,
)


class TestErrorFactories:
    """Test error factory functions."""

    def test_validation_error(self):
        exc = validation_error("Invalid input", [{"field": "name", "msg": "required"}])
        assert exc.status_code == 422
        assert exc.code == ErrorCode.VALIDATION_ERROR
        assert exc.errors == [{"field": "name", "msg": "required"}]

    def test_not_found(self):
        exc = not_found("Document", "doc-123")
        assert exc.status_code == 404
        assert exc.code == ErrorCode.NOT_FOUND
        assert "doc-123" in exc.detail

    def test_unauthorized(self):
        exc = unauthorized()
        assert exc.status_code == 401
        assert exc.code == ErrorCode.UNAUTHORIZED

    def test_forbidden(self):
        exc = forbidden("Admin only")
        assert exc.status_code == 403
        assert exc.code == ErrorCode.FORBIDDEN

    def test_rate_limited(self):
        exc = rate_limited(120)
        assert exc.status_code == 429
        assert exc.code == ErrorCode.RATE_LIMITED
        assert exc.headers["Retry-After"] == "120"

    def test_internal_error(self):
        exc = internal_error()
        assert exc.status_code == 500
        assert exc.code == ErrorCode.INTERNAL_ERROR

    def test_llm_error(self):
        exc = llm_error("Model timeout")
        assert exc.status_code == 502
        assert exc.code == ErrorCode.LLM_ERROR

    def test_database_error(self):
        exc = database_error()
        assert exc.status_code == 503
        assert exc.code == ErrorCode.DATABASE_ERROR


class TestErrorDetail:
    """Test ErrorDetail model."""

    def test_serialization(self):
        detail = ErrorDetail(
            title="Not Found",
            status=404,
            detail="Resource not found",
            code=ErrorCode.NOT_FOUND,
        )
        data = detail.model_dump(exclude_none=True)
        assert data["status"] == 404
        assert data["code"] == "NOT_FOUND"
        assert "errors" not in data  # excluded when None
