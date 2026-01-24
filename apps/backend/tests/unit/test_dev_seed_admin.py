from unittest.mock import MagicMock, patch
import pytest
from app.application.dev_seed_admin import ensure_dev_admin
from app.identity.users import UserRole, User
from app.platform.config import Settings
from uuid import uuid4

@pytest.fixture
def mock_repo():
    with patch("app.application.dev_seed_admin.get_user_by_email") as get_mock, \
         patch("app.application.dev_seed_admin.create_user") as create_mock, \
         patch("app.application.dev_seed_admin.update_user") as update_mock:
        yield get_mock, create_mock, update_mock

def test_ensure_dev_admin_disabled(mock_repo):
    get_mock, create_mock, update_mock = mock_repo
    
    settings = Settings(database_url="postgres://", dev_seed_admin=False)
    ensure_dev_admin(settings)
    
    get_mock.assert_not_called()
    create_mock.assert_not_called()
    update_mock.assert_not_called()

def test_ensure_dev_admin_fail_fast_if_not_local(mock_repo):
    get_mock, _, _ = mock_repo
    
    # app_env defaults to "development", should fail because we require "local"
    settings = Settings(
        database_url="postgres://", 
        dev_seed_admin=True, 
        app_env="development"
    )
    
    with pytest.raises(RuntimeError, match="must be 'local'"):
        ensure_dev_admin(settings)
        
    settings.app_env = "production"
    with pytest.raises(RuntimeError, match="must be 'local'"):
        ensure_dev_admin(settings)

def test_ensure_dev_admin_create_new(mock_repo):
    get_mock, create_mock, update_mock = mock_repo
    get_mock.return_value = None  # User does not exist
    
    settings = Settings(
        database_url="postgres://", 
        dev_seed_admin=True, 
        app_env="local",
        dev_seed_admin_email="test@local",
        dev_seed_admin_password="pass",
        dev_seed_admin_role="admin"
    )
    
    ensure_dev_admin(settings)
    
    get_mock.assert_called_with("test@local")
    create_mock.assert_called_once()
    update_mock.assert_not_called()
    
    # Verify arguments
    args = create_mock.call_args[1]
    assert args["email"] == "test@local"
    assert args["role"] == UserRole.ADMIN
    assert args["is_active"] is True
    # check hash logic implicitly by call success

def test_ensure_dev_admin_idempotent_existing(mock_repo):
    get_mock, create_mock, update_mock = mock_repo
    existing = User(
        id=uuid4(), 
        email="test@local", 
        password_hash="hash", 
        role=UserRole.ADMIN, 
        is_active=True
    )
    get_mock.return_value = existing
    
    settings = Settings(
        database_url="postgres://", 
        dev_seed_admin=True, 
        app_env="local",
        dev_seed_admin_email="test@local",
        dev_seed_admin_force_reset=False
    )
    
    ensure_dev_admin(settings)
    
    get_mock.assert_called_with("test@local")
    create_mock.assert_not_called()
    update_mock.assert_not_called()

def test_ensure_dev_admin_force_reset(mock_repo):
    get_mock, create_mock, update_mock = mock_repo
    existing = User(
        id=uuid4(), 
        email="test@local", 
        password_hash="old_hash", 
        role=UserRole.EMPLOYEE, 
        is_active=False
    )
    get_mock.return_value = existing
    
    settings = Settings(
        database_url="postgres://", 
        dev_seed_admin=True, 
        app_env="local",
        dev_seed_admin_email="test@local",
        dev_seed_admin_force_reset=True,
        dev_seed_admin_role="admin"
    )
    
    ensure_dev_admin(settings)
    
    get_mock.assert_called_with("test@local")
    create_mock.assert_not_called()
    update_mock.assert_called_once()
    
    kwargs = update_mock.call_args[1]
    assert kwargs["role"] == UserRole.ADMIN
    assert kwargs["is_active"] is True
    assert "password_hash" in kwargs
