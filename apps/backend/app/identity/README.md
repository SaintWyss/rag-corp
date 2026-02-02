# Layer: Identity (Auth & Access Control)

## 🎯 Misión

Esta carpeta es un **Subdominio de Soporte** dedicado exclusivamente a la Autenticación (AuthN) y Autorización (AuthZ).
Maneja usuarios, roles, permisos y la validación de credenciales.

**Qué SÍ hace:**

- Define modelos de usuario y roles (`users.py`, `auth_users.py`).
- Implementa RBAC (Role-Based Access Control) (`rbac.py`).
- Implementa lógica de autenticación dual (API Key vs JWT) (`dual_auth.py`).

**Qué NO hace:**

- No maneja la sesión HTTP directamente (eso lo hacen los middlewares).
- No es el "User Profile" del negocio (si hubiera uno, iría en `domain`).

**Analogía:**
Es el Departamento de Seguridad del edificio. Emiten las tarjetas de identificación (AuthN) y deciden qué puertas abre cada tarjeta (AuthZ).

## 🗺️ Mapa del territorio

| Recurso             | Tipo       | Responsabilidad (en humano)                                               |
| :------------------ | :--------- | :------------------------------------------------------------------------ |
| `access_control.py` | 🐍 Archivo | Lógica de bajo nivel para chequeo de acceso.                              |
| `auth.py`           | 🐍 Archivo | Helpers generales de autenticación (hashing, verify).                     |
| `auth_users.py`     | 🐍 Archivo | Modelos o lógica específica de usuarios del sistema de auth.              |
| `dual_auth.py`      | 🐍 Archivo | Estrategia híbrida: soporta API Key (Service-to-Service) y JWT (Humanos). |
| `rbac.py`           | 🐍 Archivo | **Role Based Access Control**. Define qué rol puede hacer qué acción.     |
| `users.py`          | 🐍 Archivo | Definiciones básicas de tipos de usuario.                                 |

## ⚙️ ¿Cómo funciona por dentro?

### Dual Auth (`dual_auth.py`)

El sistema permite dos formas de entrada:

1.  **JWT (Bearer Token):** Para usuarios humanos logueados frontend. Contiene `sub` (user_id) y `roles`.
2.  **API Key (X-API-Key):** Para servicios automatizados o SDKs.

### RBAC (`rbac.py`)

Define decoradores o funciones check como `require_role(ADMIN)`.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Supporting Subdomain.
- **Recibe órdenes de:** `api` (Middlewares y dependencias de seguridad).
- **Llama a:** `crosscutting` (Config).

## 👩‍💻 Guía de uso (Snippets)

### Verificar permiso en un endpoint (vía dependencia)

```python
from fastapi import Depends
from app.identity.rbac import require_role, UserRole

@router.delete("/users/{id}")
def delete_user(
    id: str,
    _auth: None = Depends(require_role(UserRole.ADMIN))
):
    ...
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevos Roles:** Agrégalos al Enum en `users.py` o `auth_users.py`.
2.  **Nuevos Permisos:** Define la regla en `rbac.py`.

## 🆘 Troubleshooting

- **Síntoma:** "403 Forbidden" aunque el token es válido.
  - **Causa:** El usuario tiene un rol que no satisface el `require_role` del endpoint.
- **Síntoma:** "401 Unauthorized".
  - **Causa:** Token expirado o API Key inválida.

## 🔎 Ver también

- [Rutas de Auth (API)](../api/README.md)
