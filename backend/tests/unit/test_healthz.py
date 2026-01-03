"""
Name: Health Check Endpoint Unit Tests

Responsibilities:
  - Test /healthz basic mode (DB only)
  - Test /healthz?full=true mode (DB + Google)
  - Verify response structure and status codes
  - Test Google API check helper

Collaborators:
  - app.main: Module under test (healthz endpoint)
  - pytest: Testing framework
  - fastapi.testclient: HTTP testing

Constraints:
  - Tests must not make real API calls
  - Must mock database and Google API

Notes:
  - Uses pytest markers for unit tests
  - Covers both modes of health check
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os


# R: Set required env vars BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("GOOGLE_API_KEY", "test-api-key")


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Clear settings cache before each test."""
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestCheckGoogleApi:
    """Tests for _check_google_api helper function."""
    
    def test_returns_disabled_without_api_key(self):
        """Should return 'disabled' when no API key."""
        # Import first while env vars are set
        from app.main import _check_google_api
        
        # Then clear the key for the test
        saved_key = os.environ.pop("GOOGLE_API_KEY", None)
        try:
            result = _check_google_api()
            assert result == "disabled"
        finally:
            if saved_key:
                os.environ["GOOGLE_API_KEY"] = saved_key
    
    @patch("google.generativeai.embed_content")
    @patch("google.generativeai.configure")
    def test_returns_available_on_success(self, mock_configure, mock_embed):
        """Should return 'available' when API responds."""
        os.environ["GOOGLE_API_KEY"] = "test-key"
        
        mock_embed.return_value = {"embedding": [0.1, 0.2, 0.3]}
        
        from app.main import _check_google_api
        result = _check_google_api()
        
        assert result == "available"
        mock_configure.assert_called_with(api_key="test-key")
    
    @patch("google.generativeai.embed_content")
    @patch("google.generativeai.configure")
    def test_returns_unavailable_on_error(self, mock_configure, mock_embed):
        """Should return 'unavailable' when API errors."""
        os.environ["GOOGLE_API_KEY"] = "test-key"
        
        mock_embed.side_effect = Exception("API error")
        
        from app.main import _check_google_api
        result = _check_google_api()
        
        assert result == "unavailable"


class TestHealthzEndpoint:
    """Tests for /healthz endpoint behavior."""
    
    @patch("app.main.get_document_repository")
    def test_healthz_returns_db_status(self, mock_get_repo):
        """Should return database connection status."""
        mock_repo = Mock()
        mock_repo.ping.return_value = True
        mock_get_repo.return_value = mock_repo
        
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        
        # Get underlying FastAPI app (unwrap middleware)
        actual_app = fastapi_app
        if hasattr(fastapi_app, "app"):
            actual_app = fastapi_app.app
        
        client = TestClient(actual_app, raise_server_exceptions=False)
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert "db" in data
        assert "ok" in data
    
    @patch("app.main._check_google_api")
    @patch("app.main.get_document_repository")
    def test_healthz_full_includes_google_status(self, mock_get_repo, mock_check_google):
        """Should include Google status when full=true."""
        mock_repo = Mock()
        mock_repo.ping.return_value = True
        mock_get_repo.return_value = mock_repo
        mock_check_google.return_value = "available"
        
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        
        actual_app = fastapi_app
        if hasattr(fastapi_app, "app"):
            actual_app = fastapi_app.app
        
        client = TestClient(actual_app, raise_server_exceptions=False)
        response = client.get("/healthz?full=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "google" in data
        assert data["google"] == "available"
    
    @patch("app.main._check_google_api")
    @patch("app.main.get_document_repository")
    def test_healthz_full_google_unavailable_sets_ok_false(self, mock_get_repo, mock_check_google):
        """Should set ok=false when Google unavailable in full mode."""
        mock_repo = Mock()
        mock_repo.ping.return_value = True
        mock_get_repo.return_value = mock_repo
        mock_check_google.return_value = "unavailable"
        
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        
        actual_app = fastapi_app
        if hasattr(fastapi_app, "app"):
            actual_app = fastapi_app.app
        
        client = TestClient(actual_app, raise_server_exceptions=False)
        response = client.get("/healthz?full=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["google"] == "unavailable"
    
    @patch("app.main._check_google_api")
    @patch("app.main.get_document_repository")
    def test_healthz_full_google_disabled_keeps_ok_true(self, mock_get_repo, mock_check_google):
        """Should keep ok=true when Google disabled (optional)."""
        mock_repo = Mock()
        mock_repo.ping.return_value = True
        mock_get_repo.return_value = mock_repo
        mock_check_google.return_value = "disabled"
        
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        
        actual_app = fastapi_app
        if hasattr(fastapi_app, "app"):
            actual_app = fastapi_app.app
        
        client = TestClient(actual_app, raise_server_exceptions=False)
        response = client.get("/healthz?full=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["google"] == "disabled"
