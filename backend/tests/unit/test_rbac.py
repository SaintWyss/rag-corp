"""
Tests for RBAC (Role-Based Access Control)
"""

from unittest.mock import patch

from app.rbac import (
    Permission,
    Role,
    RBACConfig,
    DEFAULT_ROLES,
    get_rbac_config,
    clear_rbac_cache,
    is_rbac_enabled,
)


class TestPermission:
    """Test Permission enum."""

    def test_all_permissions_have_values(self):
        """All permissions should have string values."""
        for perm in Permission:
            assert perm.value is not None
            assert isinstance(perm.value, str)

    def test_permission_format(self):
        """Permissions should follow resource:action format."""
        for perm in Permission:
            if perm != Permission.ALL:
                assert ":" in perm.value


class TestRole:
    """Test Role class."""

    def test_direct_permission(self):
        """Role should have direct permission."""
        role = Role(
            name="test",
            permissions={Permission.DOCUMENTS_READ},
        )
        assert role.has_permission(Permission.DOCUMENTS_READ, {})
        assert not role.has_permission(Permission.DOCUMENTS_CREATE, {})

    def test_wildcard_permission(self):
        """Wildcard should grant all permissions."""
        role = Role(
            name="admin",
            permissions={Permission.ALL},
        )
        assert role.has_permission(Permission.DOCUMENTS_READ, {})
        assert role.has_permission(Permission.DOCUMENTS_CREATE, {})
        assert role.has_permission(Permission.ADMIN_CONFIG, {})

    def test_inherited_permission(self):
        """Role should inherit permissions from parent."""
        parent = Role(
            name="parent",
            permissions={Permission.DOCUMENTS_READ},
        )
        child = Role(
            name="child",
            permissions={Permission.QUERY_SEARCH},
            inherits_from="parent",
        )

        registry = {"parent": parent, "child": child}

        # Child has own permission
        assert child.has_permission(Permission.QUERY_SEARCH, registry)
        # Child inherits parent permission
        assert child.has_permission(Permission.DOCUMENTS_READ, registry)
        # Child doesn't have unrelated permission
        assert not child.has_permission(Permission.ADMIN_CONFIG, registry)


class TestDefaultRoles:
    """Test default role definitions."""

    def test_admin_has_all(self):
        """Admin should have wildcard permission."""
        admin = DEFAULT_ROLES["admin"]
        assert Permission.ALL in admin.permissions

    def test_user_permissions(self):
        """User should have standard permissions."""
        user = DEFAULT_ROLES["user"]
        assert Permission.DOCUMENTS_CREATE in user.permissions
        assert Permission.DOCUMENTS_READ in user.permissions
        assert Permission.QUERY_ASK in user.permissions
        assert Permission.ADMIN_CONFIG not in user.permissions

    def test_readonly_permissions(self):
        """Readonly should only have read permissions."""
        readonly = DEFAULT_ROLES["readonly"]
        assert Permission.DOCUMENTS_READ in readonly.permissions
        assert Permission.QUERY_SEARCH in readonly.permissions
        assert Permission.DOCUMENTS_CREATE not in readonly.permissions
        assert Permission.DOCUMENTS_DELETE not in readonly.permissions


class TestRBACConfig:
    """Test RBACConfig class."""

    def test_get_role_for_key(self):
        """Should return correct role for key."""
        config = RBACConfig(
            roles=DEFAULT_ROLES,
            key_roles={"hash123": "admin", "hash456": "user"},
        )

        role = config.get_role_for_key("hash123")
        assert role is not None
        assert role.name == "admin"

        role = config.get_role_for_key("hash456")
        assert role is not None
        assert role.name == "user"

        role = config.get_role_for_key("unknown")
        assert role is None

    def test_check_permission(self):
        """Should check permission correctly."""
        config = RBACConfig(
            roles=DEFAULT_ROLES,
            key_roles={"admin_key": "admin", "user_key": "user"},
        )

        # Admin has all
        assert config.check_permission("admin_key", Permission.ADMIN_CONFIG)
        assert config.check_permission("admin_key", Permission.DOCUMENTS_CREATE)

        # User has limited
        assert config.check_permission("user_key", Permission.DOCUMENTS_CREATE)
        assert not config.check_permission("user_key", Permission.ADMIN_CONFIG)

        # Unknown key has nothing
        assert not config.check_permission("unknown", Permission.DOCUMENTS_READ)


class TestConfigParsing:
    """Test RBAC config parsing from environment."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_rbac_cache()

    def test_no_config(self):
        """Should return None when not configured."""
        with patch.dict("os.environ", {}, clear=True):
            clear_rbac_cache()
            assert get_rbac_config() is None
            assert not is_rbac_enabled()

    def test_valid_config(self):
        """Should parse valid config."""
        config_json = """{
            "roles": {
                "custom": {
                    "permissions": ["documents:read"],
                    "description": "Custom role"
                }
            },
            "key_roles": {
                "abc123": "custom"
            }
        }"""

        with patch.dict("os.environ", {"RBAC_CONFIG": config_json}):
            clear_rbac_cache()
            config = get_rbac_config()

            assert config is not None
            assert is_rbac_enabled()
            assert "custom" in config.roles
            assert config.key_roles["abc123"] == "custom"

    def test_invalid_json(self):
        """Should handle invalid JSON gracefully."""
        with patch.dict("os.environ", {"RBAC_CONFIG": "not json"}):
            clear_rbac_cache()
            assert get_rbac_config() is None
