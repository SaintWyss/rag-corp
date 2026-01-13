# Role-Based Access Control (RBAC)

**Project:** RAG Corp  
**Last Updated:** 2026-01-13

---

## Overview

RAG Corp supports fine-grained access control through RBAC, complementing the existing API key + scope system.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Flow                       │
├─────────────────────────────────────────────────────────────┤
│  Request → API Key Validation → Scope Check → RBAC Check   │
│                 ↓                    ↓             ↓        │
│            auth.py            Depends()      rbac.py       │
└─────────────────────────────────────────────────────────────┘
```

## Default Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | Full system access | `*` (wildcard) |
| `user` | Standard user | Create/read docs, search, ask |
| `readonly` | Read-only access | Read docs, search, ask |
| `ingest-only` | Automation | Create documents only |

## Permissions

```python
# Document operations
DOCUMENTS_CREATE = "documents:create"
DOCUMENTS_READ = "documents:read"
DOCUMENTS_DELETE = "documents:delete"

# Query operations
QUERY_SEARCH = "query:search"
QUERY_ASK = "query:ask"
QUERY_STREAM = "query:stream"

# Admin operations
ADMIN_METRICS = "admin:metrics"
ADMIN_HEALTH = "admin:health"
ADMIN_CONFIG = "admin:config"
```

## Configuration

### Environment Variable

```bash
RBAC_CONFIG='{
  "roles": {
    "custom-analyst": {
      "permissions": ["documents:read", "query:search", "query:ask"],
      "description": "Data analyst with query access"
    }
  },
  "key_roles": {
    "abc123hash...": "admin",
    "def456hash...": "user",
    "ghi789hash...": "custom-analyst"
  }
}'
```

### Key Hash Generation

```python
import hashlib

api_key = "your-api-key"
key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
print(key_hash)  # Use this in RBAC_CONFIG
```

## Usage in Routes

```python
from app.rbac import require_permission, require_role, Permission

# Permission-based
@router.post("/documents")
async def create_document(
    _: None = Depends(require_permission(Permission.DOCUMENTS_CREATE))
):
    ...

# Role-based
@router.delete("/admin/cache")
async def clear_cache(
    _: None = Depends(require_role("admin"))
):
    ...
```

## Role Inheritance

Roles can inherit from parent roles:

```json
{
  "roles": {
    "senior-analyst": {
      "permissions": ["documents:delete"],
      "inherits_from": "user"
    }
  }
}
```

The `senior-analyst` role will have:
- Own permission: `documents:delete`
- Inherited from `user`: `documents:create`, `documents:read`, `query:*`

## Fallback Behavior

If RBAC is not configured (`RBAC_CONFIG` not set):
- Falls back to scope-based authentication only
- No breaking changes to existing deployments

## Testing

```bash
cd backend
pytest tests/unit/test_rbac.py -v
```

## Security Considerations

- API key hashes (not raw keys) are used in configuration
- Permission checks happen after authentication
- Wildcard (`*`) should only be assigned to admin roles
- Audit logs include key hash and denied permissions
