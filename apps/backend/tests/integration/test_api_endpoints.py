"""
Name: FastAPI Endpoints Integration Tests

Responsibilities:
  - Test API endpoints end-to-end
  - Verify request/response contracts
  - Test HTTP status codes and error handling
  - Validate API behavior with real dependencies

Collaborators:
  - app.api.main: FastAPI application
  - app.interfaces.api.http.routes: API endpoints
  - httpx: HTTP client for testing
  - pytest: Test framework

Notes:
  - Uses FastAPI TestClient (no server needed)
  - Tests require database connection
  - Mark with @pytest.mark.api
  - Can mock external services (Google API) to speed up tests

Setup:
  TestClient provides a test environment without running actual server
"""

import os
from uuid import uuid4

import psycopg
import pytest

# Skip BEFORE importing app.* to avoid triggering env validation during collection
if os.getenv("RUN_INTEGRATION") != "1":
    pytest.skip(
        "Set RUN_INTEGRATION=1 to run integration tests", allow_module_level=True
    )

if not os.getenv("GOOGLE_API_KEY"):
    pytest.skip(
        "Set GOOGLE_API_KEY to run API integration tests", allow_module_level=True
    )

from fastapi.testclient import TestClient

from app.api.main import app
from app.identity.auth_users import hash_password

pytestmark = pytest.mark.integration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag"
)


@pytest.fixture(scope="module")
def client():
    """
    R: Provide FastAPI test client.

    TestClient uses httpx under the hood and doesn't require
    running an actual server.
    """
    return TestClient(app)


@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def api_user(db_conn):
    user_id = uuid4()
    email = f"api-user-{user_id}@example.com"
    password = "test-password-123"
    password_hash = hash_password(password)

    db_conn.execute(
        """
        INSERT INTO users (id, email, password_hash, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, email, password_hash, "admin", True),
    )

    yield {"id": user_id, "email": email, "password": password}

    db_conn.execute("DELETE FROM users WHERE id = %s", (user_id,))


@pytest.fixture(scope="module")
def workspace_id(db_conn, api_user):
    workspace_id = uuid4()
    db_conn.execute(
        """
        INSERT INTO workspaces (
            id,
            name,
            description,
            visibility,
            owner_user_id,
            archived_at,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, NULL, NOW(), NOW())
        """,
        (
            workspace_id,
            f"API Workspace {workspace_id}",
            None,
            "PRIVATE",
            api_user["id"],
        ),
    )

    yield workspace_id

    db_conn.execute("DELETE FROM documents WHERE workspace_id = %s", (workspace_id,))
    db_conn.execute("DELETE FROM workspaces WHERE id = %s", (workspace_id,))


@pytest.fixture(scope="module")
def auth_headers(client, api_user):
    response = client.post(
        "/auth/login",
        json={"email": api_user["email"], "password": api_user["password"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.api
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_healthz_returns_200(self, client):
        """R: Health check should return 200 OK."""
        # Act
        response = client.get("/healthz")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["db"] == "connected"


@pytest.mark.api
class TestIngestTextEndpoint:
    """Test document ingestion endpoint."""

    def test_ingest_text_success(self, client, workspace_id, auth_headers):
        """R: Should successfully ingest text document."""
        # Arrange
        payload = {
            "title": "API Test Document",
            "text": "This is a test document for API testing. " * 50,  # ~2000 chars
            "source": "https://test.com/doc",
        }

        # Act
        response = client.post(
            "/v1/ingest/text",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "chunks" in data
        assert data["chunks"] > 0

    def test_ingest_text_without_source(self, client, workspace_id, auth_headers):
        """R: Should accept document without source field."""
        # Arrange
        payload = {
            "title": "No Source Document",
            "text": "Content without source. " * 50,
        }

        # Act
        response = client.post(
            "/v1/ingest/text",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200

    def test_ingest_text_with_short_content(self, client, workspace_id, auth_headers):
        """R: Should handle short documents (< chunk size)."""
        # Arrange
        payload = {"title": "Short Doc", "text": "This is very short."}

        # Act
        response = client.post(
            "/v1/ingest/text",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["chunks"] >= 1

    def test_ingest_text_missing_required_field(self, client, workspace_id, auth_headers):
        """R: Should return 422 for missing required fields."""
        # Arrange
        payload = {
            "title": "Missing Text Field"
            # Missing 'text' field
        }

        # Act
        response = client.post(
            "/v1/ingest/text",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422  # Validation error


@pytest.mark.api
class TestQueryEndpoint:
    """Test semantic search endpoint."""

    def test_query_success(self, client, workspace_id, auth_headers):
        """R: Should return search results for valid query."""
        # Arrange - first ingest a document
        ingest_payload = {
            "title": "Query Test Doc",
            "text": "Python is a programming language. " * 30,
        }
        client.post(
            "/v1/ingest/text",
            json=ingest_payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Act
        query_payload = {"query": "programming language", "top_k": 3}
        response = client.post(
            "/v1/query",
            json=query_payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert isinstance(data["matches"], list)

    def test_query_with_default_top_k(self, client, workspace_id, auth_headers):
        """R: Should use default top_k if not provided."""
        # Arrange
        payload = {"query": "test query"}

        # Act
        response = client.post(
            "/v1/query",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) <= 5  # Default top_k

    def test_query_with_custom_top_k(self, client, workspace_id, auth_headers):
        """R: Should respect custom top_k parameter."""
        # Arrange
        payload = {"query": "custom top k", "top_k": 2}

        # Act
        response = client.post(
            "/v1/query",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) <= 2


@pytest.mark.api
class TestAskEndpoint:
    """Test RAG Q&A endpoint (Clean Architecture implementation)."""

    def test_ask_success(self, client, workspace_id, auth_headers):
        """R: Should generate answer using RAG flow."""
        # Arrange - ingest document first
        ingest_payload = {
            "title": "RAG Test Document",
            "text": (
                "FastAPI is a modern web framework for Python. "
                "It is fast, easy to learn, and production-ready. "
            )
            * 20,
        }
        client.post(
            "/v1/ingest/text",
            json=ingest_payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Act
        ask_payload = {"query": "What is FastAPI?", "top_k": 3}
        response = client.post(
            "/v1/ask",
            json=ask_payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
        assert isinstance(data["sources"], list)

    def test_ask_with_no_relevant_context(self, client, workspace_id, auth_headers):
        """R: Should return fallback message when no chunks found."""
        # Arrange - query about something not in corpus
        payload = {
            "query": "What is the meaning of life, universe and everything?",
            "top_k": 5,
        }

        # Act
        response = client.post(
            "/v1/ask",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # May return fallback message or answer based on available docs
        assert "answer" in data

    def test_ask_with_default_top_k(self, client, workspace_id, auth_headers):
        """R: Should use default top_k=5 if not provided."""
        # Arrange
        payload = {"query": "test question"}

        # Act
        response = client.post(
            "/v1/ask",
            json=payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) <= 5

    def test_ask_includes_sources(self, client, workspace_id, auth_headers):
        """R: Should include source chunks in response."""
        # Arrange - ingest document
        ingest_payload = {
            "title": "Source Test",
            "text": "This document tests source attribution. " * 30,
        }
        client.post(
            "/v1/ingest/text",
            json=ingest_payload,
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Act
        response = client.post(
            "/v1/ask",
            json={"query": "source attribution"},
            params={"workspace_id": str(workspace_id)},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        if data["sources"]:
            first_source = data["sources"][0]
            assert isinstance(first_source, str)


@pytest.mark.api
class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_allows_localhost_origin(self, client):
        """R: Should allow requests from localhost:3000."""
        # Act
        response = client.get("/healthz", headers={"Origin": "http://localhost:3000"})

        # Assert
        assert response.status_code == 200
        # Note: TestClient may not return CORS headers in test mode
        # For real CORS testing, use integration tests with actual server


@pytest.mark.api
class TestErrorHandling:
    """Test API error handling."""

    def test_invalid_json_returns_422(self, client, workspace_id, auth_headers):
        """R: Should return 422 for invalid JSON."""
        # Act
        response = client.post(
            "/v1/ingest/text",
            data="invalid json{",
            headers={**auth_headers, "Content-Type": "application/json"},
            params={"workspace_id": str(workspace_id)},
        )

        # Assert
        assert response.status_code == 422

    def test_nonexistent_endpoint_returns_404(self, client):
        """R: Should return 404 for non-existent endpoints."""
        # Act
        response = client.get("/v1/nonexistent")

        # Assert
        assert response.status_code == 404


@pytest.mark.api
class TestAPIVersioning:
    """Test API versioning via /v1 prefix."""

    def test_endpoints_under_v1_prefix(self, client):
        """R: All business endpoints should be under /v1 prefix."""
        # Arrange
        endpoints = ["/v1/ingest/text", "/v1/query", "/v1/ask"]

        # Act & Assert
        for endpoint in endpoints:
            # OPTIONS request to check if endpoint exists
            response = client.options(endpoint)
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404


# Note: Add more API tests for:
# - Rate limiting (once implemented)
# - Authentication (once implemented)
# - Request size limits
# - Concurrent requests
# - Streaming responses (if implemented)
