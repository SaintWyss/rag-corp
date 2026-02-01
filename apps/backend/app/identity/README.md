# Identity Layer

## 🎯 Propósito

Este módulo (`app/identity`) gestiona la **Seguridad, Autenticación y Autorización**.
Implementa un modelo de **Dual Auth** que unifica dos mundos:

1.  **Usuarios Humanos**: Autenticados vía **JWT** (Login). Tienen Roles (`admin`, `employee`).
2.  **Servicios/Automations**: Autenticados vía **API Key**. Tienen Permisos granulares o Roles RBAC.

El objetivo es proveer una identidad unificada (`Principal`) a la capa de aplicación, sin que esta deba preocuparse por el mecanismo de origen.

---

## 🔑 Dual Auth Model

El sistema decide la identidad basándose en los headers presentes:

| Header                      | Mecanismo   | Principal Type | Validación                     |
| :-------------------------- | :---------- | :------------- | :----------------------------- |
| `Authorization: Bearer ...` | **JWT**     | `USER`         | Firma, Expiración, Claims.     |
| `Cookie: access_token=...`  | **JWT**     | `USER`         | Firma, Expiración, Claims.     |
| `X-API-Key: ...`            | **API Key** | `SERVICE`      | Hash en memoria, Config (Env). |

Si ambos están presentes, **JWT tiene precedencia**.

---

## 🧩 Componentes Principales

| Archivo             | Rol                 | Descripción                                                            |
| :------------------ | :------------------ | :--------------------------------------------------------------------- |
| `auth_users.py`     | **JWT Handler**     | Emisión y validación de tokens JWT. Hashing de passwords (Argon2).     |
| `auth.py`           | **API Key Handler** | Validación de API Keys en tiempo constante. Manejo de Scopes legacy.   |
| `dual_auth.py`      | **Unificador**      | Define el objeto `Principal`. Expone dependencias `require_principal`. |
| `rbac.py`           | **Autorización**    | Motor de Roles y Permisos. Carga `RBAC_CONFIG` JSON.                   |
| `users.py`          | **Modelo**          | Definición de `UserRole` (Enum) y dataclass `User`.                    |
| `access_control.py` | **Policy Ref**      | Reglas de acceso a recursos específicos (ej: Documentos).              |

---

## 🛡️ RBAC & Permisos

El sistema soporta dos modos de autorización para API Keys (definido por configuración):

1.  **RBAC (Recomendado)**:
    - Se define un JSON en `RBAC_CONFIG`.
    - Mapea Hash de Key -> Rol -> Permisos.
    - Ejemplo: Key "CI-Bot" -> Rol "Ingestor" -> `documents:create`.

2.  **Scopes (Legacy/Simple)**:
    - Se define en `API_KEYS_CONFIG`.
    - Mapea Key -> Lista de Scopes (`ingest`, `ask`).
    - El sistema traduce internamente Scopes a Permisos.

---

## 🚀 Guía de Uso (FastAPI Dependencies)

### Proteger un endpoint para Usuarios (Humanos)

```python
from app.identity.auth_users import require_role, UserRole

@router.delete("/users/{id}")
def delete_user(user: User = Depends(require_role(UserRole.ADMIN))):
    ...
```

### Proteger un endpoint para Cualquier Agente (Dual)

```python
from app.identity.dual_auth import require_principal, Permission

@router.post("/query")
def query_rag(principal = Depends(require_principal(Permission.QUERY_ASK))):
    if principal.user:
        print(f"User: {principal.user.email}")
    else:
        print(f"Service Key Hash: {principal.service.api_key_hash}")
```
