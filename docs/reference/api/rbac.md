# RBAC para API Keys
Fuente de verdad: `apps/backend/app/identity/rbac.py` y `apps/backend/app/identity/auth.py`.

## Resumen
- RBAC aplica a **API keys** (`X-API-Key`).
- Si existe `RBAC_CONFIG`, la autorización se resuelve por roles/permisos.
- Si **no** existe `RBAC_CONFIG` pero sí `API_KEYS_CONFIG`, se aplica el fallback por scopes.
- Si no hay ninguna configuración, la auth por API key se considera deshabilitada.

## Permisos disponibles
Definidos en `Permission` (`apps/backend/app/identity/rbac.py`):
- `documents:create`
- `documents:read`
- `documents:delete`
- `query:search`
- `query:ask`
- `query:stream`
- `admin:metrics`
- `admin:health`
- `admin:config`
- `*` (wildcard)

## Scopes → permisos
Mapeo `SCOPE_PERMISSIONS` (`apps/backend/app/identity/rbac.py`):
- `ingest` → `documents:create`, `documents:read`, `documents:delete`
- `ask` → `documents:read`, `query:search`, `query:ask`, `query:stream`
- `metrics` → `admin:metrics`

## Roles por defecto
`DEFAULT_ROLES` en `apps/backend/app/identity/rbac.py`:
- `admin` → `*`
- `user` → create/read docs + search/ask/stream
- `readonly` → read docs + search/ask
- `ingest-only` → create docs

## Configuración
### RBAC_CONFIG
Se parsea desde env en `apps/backend/app/identity/rbac.py`.

Shape esperado:
```json
{
  "roles": {
    "custom-role": {
      "permissions": ["documents:read"],
      "inherits_from": "readonly",
      "description": "Rol personalizado"
    }
  },
  "key_roles": {
    "<key_hash>": "admin"
  }
}
```

### API_KEYS_CONFIG (fallback)
Se parsea en `apps/backend/app/identity/auth.py`.

Shape esperado:
```json
{
  "mi-api-key": ["ingest", "ask"],
  "otra-key": ["*"]
}
```

### Hash de API key
El hash recortado se calcula con SHA-256 y longitud fija (`_KEY_HASH_LEN`) en `apps/backend/app/identity/auth.py`.

## Referencias técnicas
- RBAC → `apps/backend/app/identity/rbac.py`
- API keys (auth) → `apps/backend/app/identity/auth.py`
