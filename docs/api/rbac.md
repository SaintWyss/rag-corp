# Role-Based Access Control (RBAC)

**Project:** RAG Corp  
**Last Updated:** 2026-01-22

---

## Overview

RBAC agrega permisos a las API keys existentes. El flujo es:

1) API key valida (si `API_KEYS_CONFIG` esta configurado)  
2) RBAC check (si `RBAC_CONFIG` esta configurado)  
3) Fallback a scopes legacy cuando no hay RBAC

Notas:
- RBAC aplica solo a **API keys**.
- JWT (usuarios) usa roles `admin|employee` via `/auth/*`.

---

## Permisos

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

---

## Scopes legacy -> permisos

En ausencia de RBAC, los scopes se mapean asi:

| Scope | Permisos |
|-------|----------|
| `ingest` | `documents:create`, `documents:read`, `documents:delete` |
| `ask` | `documents:read`, `query:search`, `query:ask`, `query:stream` |
| `metrics` | `admin:metrics` |
| `*` | `*` |

---

## Default Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | Full system access | `*` |
| `user` | Standard user | create/read docs, search, ask, stream |
| `readonly` | Read-only access | read docs, search, ask |
| `ingest-only` | Automation | create docs only |

---

## JWT Roles (UI)

Para autenticacion de usuarios (JWT), los roles son:

- `admin`
- `employee`

Los guards de endpoints combinan JWT role gates con permisos RBAC para API keys.

---

## Configuration

### RBAC_CONFIG

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
    "def456hash...": "user"
  }
}'
```

### Key hash

```python
import hashlib

api_key = "your-api-key"
key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
print(key_hash)
```

---

## Usage in Routes

```python
from app.rbac import require_permissions, Permission

@router.post("/ingest/text")
def ingest(_: None = Depends(require_permissions(Permission.DOCUMENTS_CREATE))):
    ...
```

Para endpoints admin de `/auth/users`, el permiso requerido es `admin:config` (solo RBAC).

---

## Fallback Behavior

- Si `RBAC_CONFIG` no esta configurado: usa scopes legacy.
- Si `API_KEYS_CONFIG` y `RBAC_CONFIG` estan vacias: auth deshabilitada.

---

## Testing

```bash
pnpm test:backend:unit
```
