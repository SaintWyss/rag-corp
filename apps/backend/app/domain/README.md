# domain
Como un **contrato legal**: define reglas y términos del negocio sin IO ni frameworks.

## 🎯 Misión
Este módulo define el lenguaje del negocio del backend: entidades, objetos de valor, políticas puras y puertos (Protocols) que el resto del sistema implementa o consume.

### Qué SÍ hace
- Modela entidades centrales (`Document`, `Workspace`, `Chunk`, `ConversationMessage`, `QueryResult`).
- Define puertos de repositorios y servicios externos.
- Provee políticas puras (ej. acceso a workspace).
- Normaliza metadata de entrada (`allowed_roles`, `tags`).

### Qué NO hace (y por qué)
- No accede a DB/colas/storage ni SDKs externos.
  - Razón: el dominio debe ser portable y testeable.
  - Consecuencia: el IO se implementa en `infrastructure/`.
- No depende de FastAPI ni transporte.
  - Razón: el dominio no conoce HTTP.
  - Consecuencia: Interfaces solo adapta.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del dominio. |
| `__init__.py` | Archivo Python | Re-exports de la API pública del dominio. |
| `access.py` | Archivo Python | Normaliza `allowed_roles` desde metadata. |
| `audit.py` | Archivo Python | Modelo de evento de auditoría del dominio. |
| `cache.py` | Archivo Python | Puerto de cache de embeddings. |
| `entities.py` | Archivo Python | Entidades y enums del dominio. |
| `repositories.py` | Archivo Python | Protocols de persistencia (repositorios). |
| `services.py` | Archivo Python | Protocols de servicios externos (LLM, embeddings, storage, queue). |
| `tags.py` | Archivo Python | Normalización de tags. |
| `value_objects.py` | Archivo Python | Objetos de valor y tipos inmutables. |
| `workspace_policy.py` | Archivo Python | Políticas puras de acceso a workspaces. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Normalización de metadata**
  - Input: metadata libre.
  - Proceso: `access.py` y `tags.py` limpian y deduplican.
  - Output: listas estables.
- **Políticas**
  - Input: actor + workspace/ACL.
  - Proceso: `workspace_policy.py` decide read/write/share.
  - Output: booleanos de acceso.
- **Puertos (Protocols)**
  - Input: necesidades del sistema (persistir, embeber, almacenar, encolar).
  - Proceso: `repositories.py`/`services.py` definen contratos.
  - Output: interfaces que Infrastructure implementa.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Core Domain.
- **Recibe órdenes de:** Application (casos de uso).
- **Llama a:** no aplica (no IO).
- **Reglas de límites:** no importar `infrastructure/` ni `interfaces/`.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.domain.entities import Document

doc = Document(id=uuid4(), title="Manual")
doc.mark_deleted()
```

```python
from app.domain.workspace_policy import WorkspaceActor, can_read_workspace
from app.identity.users import UserRole
from uuid import UUID

actor = WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.EMPLOYEE)
allowed = can_read_workspace(actor=actor, workspace_visibility="private", actor_has_acl=False)
```

```python
from app.domain.access import normalize_allowed_roles

allowed_roles = normalize_allowed_roles({"allowed_roles": ["EMPLOYEE", " "]})
```

## 🧩 Cómo extender sin romper nada
- Si agregás una entidad nueva, mantené invariantes en `entities.py`.
- Si agregás un puerto, definalo en `repositories.py` o `services.py` y actualizá adapters.
- Si agregás una policy, mantenela pura (sin IO).
- Wiring: los adapters se seleccionan en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/domain/`, integration si el puerto toca DB en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** imports profundos repetidos.
  - **Causa probable:** falta re-export en `__init__.py`.
  - **Dónde mirar:** `domain/__init__.py`.
  - **Solución:** exponer símbolos estables.
- **Síntoma:** `can_read_workspace` devuelve `False` inesperado.
  - **Causa probable:** actor incompleto o visibilidad no contemplada.
  - **Dónde mirar:** `workspace_policy.py`.
  - **Solución:** revisar construcción de `WorkspaceActor` y ACL.
- **Síntoma:** `allowed_roles` queda vacío.
  - **Causa probable:** metadata mal formada.
  - **Dónde mirar:** `access.py`.
  - **Solución:** validar formato antes de persistir.
- **Síntoma:** Application importa infraestructura.
  - **Causa probable:** contrato faltante en dominio.
  - **Dónde mirar:** `repositories.py` / `services.py`.
  - **Solución:** mover el contrato al dominio.

## 🔎 Ver también
- `../application/README.md`
- `../identity/README.md`
- `../infrastructure/README.md`
- `../container.py`
