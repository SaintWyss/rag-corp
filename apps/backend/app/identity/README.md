# Identity (auth y permisos)

## 🎯 Misión
Resolver autenticación y autorización del backend: API keys, JWT, RBAC y helpers de acceso para documentos y workspaces.

**Qué SÍ hace**
- Valida API keys y scopes (X-API-Key).
- Emite y valida JWT para usuarios.
- Unifica credenciales en un `Principal` (dual auth).
- Aplica RBAC/permisos a endpoints y recursos.

**Qué NO hace**
- No define reglas de negocio de documentos o workspaces.
- No accede directamente a la DB salvo los repos necesarios de auth.

**Analogía (opcional)**
- Es el control de acceso del edificio: decide quién entra y a qué puertas.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `access_control.py` | Archivo Python | Policy de acceso a documentos según Principal. |
| 🐍 `auth.py` | Archivo Python | API keys: validación, scopes y dependencias FastAPI. |
| 🐍 `auth_users.py` | Archivo Python | JWT: hash de passwords, emisión/validación de tokens. |
| 🐍 `dual_auth.py` | Archivo Python | Principal unificado (JWT + API key) y permisos. |
| 🐍 `rbac.py` | Archivo Python | RBAC para API keys (permissions, roles, config). |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `users.py` | Archivo Python | Modelos de usuario y roles (User, UserRole). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: headers/cookies (JWT) o `X-API-Key`.
- **Proceso**: validación criptográfica + RBAC/scopes + construcción de `Principal`.
- **Output**: dependencias FastAPI que permiten/deniegan el acceso.

Tecnologías/librerías usadas aquí:
- PyJWT, argon2-cffi, FastAPI security.

Flujo típico:
- `auth_users.authenticate_user()` valida credenciales y emite JWT.
- `dual_auth.require_principal()` construye Principal (USER o SERVICE).
- `rbac.require_permissions()` aplica permisos a endpoints.

## 🔗 Conexiones y roles
- Rol arquitectónico: Application (seguridad/identidad).
- Recibe órdenes de: interfaces HTTP (dependencias FastAPI).
- Llama a: repos de usuarios (infra), settings y logger.
- Contratos y límites: lógica de auth no vive en dominio ni en infraestructura genérica.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.identity.users import User, UserRole
from app.identity.auth_users import create_access_token

user = User(
    id=uuid4(),
    email="admin@local",
    password_hash="hashed",
    role=UserRole.ADMIN,
    is_active=True,
)

token, expires_in = create_access_token(user)
```

## 🧩 Cómo extender sin romper nada
- Agrega permisos nuevos en `rbac.Permission` y mapéalos en `SCOPE_PERMISSIONS`.
- Si sumás roles de usuario, ajusta `users.py` y dependencias de `auth_users.py`.
- Mantén `dual_auth` como punto único de unificación de credenciales.
- Documenta nuevos headers/cookies si cambian los contratos.

## 🆘 Troubleshooting
- Síntoma: 401 en endpoints con API key → Causa probable: key inválida → Mirar `auth.py`.
- Síntoma: 403 con API key válida → Causa probable: permisos insuficientes → Mirar `rbac.py`.
- Síntoma: JWT inválido → Causa probable: `JWT_SECRET` o expiración → Mirar `auth_users.py` y `.env`.

## 🔎 Ver también
- [Interfaces HTTP](../interfaces/api/http/README.md)
- [Domain](../domain/README.md)
- [Crosscutting errors](../crosscutting/error_responses.py)
