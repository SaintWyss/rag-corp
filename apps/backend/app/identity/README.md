# identity
Como un **control de acceso**: unifica API keys y JWT en un principal común y aplica permisos consistentes.

## 🎯 Misión
Este módulo define la capa de **identidad y autorización** del backend. Provee autenticación por API key y JWT, resuelve un principal unificado y expone dependencias FastAPI para exigir permisos/roles en el borde HTTP.

### Qué SÍ hace
- Valida API keys con comparación en tiempo constante y scopes configurables.
- Emite/valida JWT para usuarios y expone dependencias de auth.
- Construye un `Principal` unificado (USER o SERVICE) con permisos RBAC.
- Aplica helpers de acceso a documentos (`can_access_document`).

### Qué NO hace (y por qué)
- No ejecuta lógica de negocio de dominio. Razón: las políticas de negocio viven en Domain/Application. Consecuencia: identity solo decide autenticación/autorización y el shape del actor.
- No accede a DB directamente salvo repositorios de usuario vía infraestructura. Razón: el storage real está en `infrastructure/`. Consecuencia: cualquier IO adicional debe modelarse como puerto/adaptador.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de la capa de identidad. |
| `access_control.py` | Archivo Python | Policy helper para acceso a documentos por principal. |
| `auth.py` | Archivo Python | API keys: parseo de config, scopes y dependencias FastAPI. |
| `auth_users.py` | Archivo Python | JWT de usuarios: hash/verify, create/decode token, dependencias. |
| `dual_auth.py` | Archivo Python | Principal unificado (JWT + API key) y dependencias de permisos/roles. |
| `rbac.py` | Archivo Python | RBAC para API keys: permisos, roles y dependencias. |
| `users.py` | Archivo Python | `UserRole` y modelo `User` usados por auth. |
## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **API key**
- Input: header `X-API-Key`.
- Proceso: `auth.py` parsea `API_KEYS_CONFIG`, valida key y scopes; `rbac.py` puede reemplazar scopes con `RBAC_CONFIG`.
- Output: permisos disponibles para el request.
- **JWT (usuarios)**
- Input: `Authorization: Bearer ...` o cookie.
- Proceso: `auth_users.py` valida firma/exp/claims, resuelve usuario y rol.
- Output: `User` autenticado o 401/403.
- **Principal unificado**
- Input: request HTTP.
- Proceso: `dual_auth.require_principal()` elige JWT si existe, si no API key; construye `Principal`.
- Output: `Principal` con `principal_type=USER|SERVICE`.
- **Acceso a documentos**
- Input: `Document` + `Principal`.
- Proceso: `access_control.can_access_document` aplica reglas defensivas (default allow si no hay principal o allowed_roles).
- Output: booleano de acceso.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Interfaces/Security boundary (authN + authZ).
- **Recibe órdenes de:** routers HTTP mediante dependencias FastAPI.
- **Llama a:** repositorios de usuario (infra) y settings (`crosscutting.config`).
- **Reglas de límites:** no contiene lógica de negocio ni IO adicional fuera de auth.

## 👩‍💻 Guía de uso (Snippets)
```python
# Requerir principal (USER o SERVICE)
from app.identity.dual_auth import require_principal

@router.get("/secure")
def secure_route(principal=Depends(require_principal())):
    return {"ok": True}
```

```python
# Requerir scope por API key
from app.identity.auth import require_scope

@router.post("/ingest")
def ingest(_auth=Depends(require_scope("ingest"))):
    return {"ok": True}
```

```python
# Emitir JWT para un usuario
from app.identity.auth_users import create_access_token

token, expires_in = create_access_token(user)
```

## 🧩 Cómo extender sin romper nada
- Si agregás permisos nuevos, definilos en `identity/rbac.py` y actualizá el mapping de scopes si corresponde.
- Si agregás un rol nuevo de usuario, extendé `UserRole` en `users.py` y ajustá dependencias en `dual_auth.py`.
- Si necesitás un servicio adicional para auth, cablealo en `app/container.py` y consumilo desde identity (sin importar infra directo en routers).
- Tests: unit en `apps/backend/tests/unit/identity/`, integration para flujos con DB en `apps/backend/tests/integration/`, e2e si se valida el flujo completo.

## 🆘 Troubleshooting
- **Síntoma:** 401 en endpoints protegidos.
- **Causa probable:** token/JWT inválido o falta API key.
- **Dónde mirar:** `identity/auth_users.py` o `identity/auth.py`.
- **Solución:** revisar headers/cookie y settings de auth.
- **Síntoma:** 403 con API key válida.
- **Causa probable:** permisos RBAC o scopes insuficientes.
- **Dónde mirar:** `identity/rbac.py` y `API_KEYS_CONFIG`/`RBAC_CONFIG`.
- **Solución:** actualizar permisos o scopes del key.
- **Síntoma:** auth “deshabilitada” sin querer.
- **Causa probable:** `API_KEYS_CONFIG` vacío y `RBAC_CONFIG` ausente.
- **Dónde mirar:** `crosscutting/config.py` y variables de entorno.
- **Solución:** setear config de keys o RBAC.
- **Síntoma:** `ModuleNotFoundError` al usar scripts de auth.
- **Causa probable:** cwd incorrecto o `PYTHONPATH` no incluye `apps/backend`.
- **Dónde mirar:** `pwd` y logs.
- **Solución:** ejecutar desde `apps/backend/`.

## 🔎 Ver también
- `../interfaces/api/http/README.md`
- `../crosscutting/README.md`
- `../domain/README.md`
- `../container.py`
