# domain

El **contrato legal del negocio**: define términos, reglas y contratos, sin implementar base de datos, colas ni frameworks.

## 🎯 Misión

Este módulo define el **lenguaje del negocio** del backend: entidades, objetos de valor, políticas puras y puertos (Protocols) que el resto del sistema usa para construir features sin acoplarse a infraestructura.

Recorridos rápidos por intención:

- **Quiero entender el modelo principal (Document/Workspace/Chunk/Conversation)** → `entities.py`
- **Quiero ver decisiones de acceso (read/write/ACL)** → `workspace_policy.py`
- **Quiero ver contratos de persistencia (repositorios)** → `repositories.py`
- **Quiero ver contratos de servicios externos (LLM/embeddings/storage/queue/extractor/chunker)** → `services.py`
- **Quiero ver normalización de metadata** → `access.py` (roles) / `tags.py` (tags)
- **Quiero ver auditoría de eventos** → `audit.py`
- **Quiero ver objetos de valor usados por UI/auditoría** → `value_objects.py`
- **Quiero ver tests del dominio** → `apps/backend/tests/unit/domain/`

### Qué SÍ hace

- Modela entidades centrales del sistema (ej. `Document`, `Workspace`, `Chunk`, `QueryResult`, `ConversationMessage`).
- Define **contratos** (Protocols) para repositorios y servicios externos; Application depende de ellos e Infrastructure los implementa.
- Provee políticas puras (ej. acceso a workspaces) y normalizadores (roles/tags) para transformar entrada libre en datos consistentes.
- Mantiene el dominio portable: el mismo núcleo funciona en API, worker y tests sin cambios.

### Qué NO hace (y por qué)

- No accede a base de datos, colas, storage ni APIs externas.
  - **Razón:** el dominio no puede depender de detalles de IO.
  - **Impacto:** los puertos se definen acá; la ejecución concreta vive en Infrastructure y se inyecta desde `app/container.py`.

- No depende de FastAPI, Redis, S3 ni SDKs de proveedores.
  - **Razón:** mantener el núcleo testeable con unit tests puros y evitar lock-in.
  - **Impacto:** los modelos y policies se importan igual desde HTTP (`interfaces`) y desde el worker.

## 🗺️ Mapa del territorio

| Recurso               | Tipo           | Responsabilidad (en humano)                                                                             |
| :-------------------- | :------------- | :------------------------------------------------------------------------------------------------------ |
| `__init__.py`         | Archivo Python | API pública del dominio (re-exports) para imports estables y poco acoplamiento.                         |
| `access.py`           | Archivo Python | Normaliza `allowed_roles` desde metadata (strip + lower + filtra roles válidos).                        |
| `audit.py`            | Archivo Python | Modelo `AuditEvent` (append-only) para trazabilidad del sistema.                                        |
| `cache.py`            | Archivo Python | Puerto `EmbeddingCachePort` para cachear embeddings (get/set, TTL decidido por implementación).         |
| `entities.py`         | Archivo Python | Entidades y enums (`Document`, `Workspace`, `Chunk`, `WorkspaceVisibility`, etc.).                      |
| `repositories.py`     | Archivo Python | Puertos de persistencia: documentos/chunks, workspaces/ACL, conversaciones, auditoría y feedback.       |
| `services.py`         | Archivo Python | Puertos de servicios externos: embeddings, LLM (incluye stream), chunker, storage, extractor y queue.   |
| `tags.py`             | Archivo Python | Normaliza `tags` desde metadata (limpia, deduplica, orden estable).                                     |
| `value_objects.py`    | Archivo Python | Objetos de valor (inmutables): fuentes, confidence, filtros, quotas, feedback, auditoría de respuestas. |
| `workspace_policy.py` | Archivo Python | Policy pura de acceso a workspaces (`can_read_workspace`, `can_write_workspace`, `can_manage_acl`).     |
| `README.md`           | Documento      | Portada + índice del dominio y reglas de límites.                                                       |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output. En domain no hay side-effects: no se escribe DB, no se llama HTTP, no se encola nada.

### 1) Entidades: estado mínimo + operaciones coherentes

- **Input:** datos del negocio (ids, títulos, metadata, estado).
- **Proceso:** las entidades encapsulan operaciones pequeñas y coherentes.
  - `Document` centraliza soft delete (`mark_deleted`/`restore`) y seteo de estado de procesamiento (`set_processing_status`).
  - `Workspace` centraliza archivado (`archive`/`unarchive`) y expone `visibility` (`WorkspaceVisibility`).

- **Output:** instancias consistentes que Application persiste y que Interfaces serializa.

### 2) Normalización de metadata (roles/tags)

- **Input:** `metadata` (diccionario con valores libres provenientes de UI/imports).
- **Proceso:**
  - `normalize_allowed_roles(metadata)` filtra roles inválidos contra `identity.users.UserRole` y devuelve una lista limpia.
  - `normalize_tags(metadata)` limpia y deduplica tags conservando orden de aparición.

- **Output:** listas normalizadas listas para persistencia y filtrado.

### 3) Políticas puras de acceso (workspace_policy)

- **Input:** `Workspace` + `WorkspaceActor` (user_id + role) y, en modo SHARED, lista de `shared_user_ids`.
- **Proceso:**
  - `can_read_workspace` implementa la regla de lectura (admin/owner/ORG_READ/SHARED por ACL).
  - `can_write_workspace` permite escritura solo a admin/owner.
  - `can_manage_acl` sigue las mismas reglas que write.

- **Output:** una decisión booleana que Application usa para fail-fast o para filtrar listados.

### 4) Puertos (Protocols): fronteras del sistema

- **Input:** necesidades del sistema (persistir, buscar, extraer, embeber, almacenar archivos, encolar jobs).
- **Proceso:**
  - `repositories.py` define contratos de persistencia (`DocumentRepository`, `WorkspaceRepository`, `WorkspaceAclRepository`, `ConversationRepository`, `AuditEventRepository`, `FeedbackRepository`, `AnswerAuditRepository`).
  - `services.py` define contratos de servicios externos (`EmbeddingService`, `LLMService`, `TextChunkerService`, `FileStoragePort`, `DocumentTextExtractor`, `DocumentProcessingQueue`).
  - `cache.py` agrega un puerto mínimo para cache de embeddings (`EmbeddingCachePort`).

- **Output:** interfaces que Infrastructure implementa y el Container inyecta en los casos de uso.

### 5) Objetos de valor: igualdad por valor + serialización

- **Input:** datos estructurados que UI y auditoría necesitan (fuentes, confianza, filtros, cuotas, votos, auditoría de respuestas).
- **Proceso:** validan invariantes en `__post_init__` y ofrecen `to_dict()` para salida estable.
- **Output:** estructuras inmutables que viajan entre capas sin acoplarse a transporte.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Core Domain.

- **Recibe órdenes de:**
  - _Application_ (use cases), que crea/actualiza entidades, evalúa policies y opera a través de puertos.

- **Llama a:**
  - No aplica: el dominio define contratos; no ejecuta IO.

- **Reglas de límites (imports/ownership):**
  - `app/domain/**` no importa `app/infrastructure/**`, `app/interfaces/**` ni `app/api/**`.
  - Se permite stdlib + `typing` + `dataclasses`.
  - Protocols son la frontera: Application depende de Protocols; Infrastructure implementa Protocols.
  - `__init__.py` se usa para reducir imports profundos repetidos.

## 👩‍💻 Guía de uso (Snippets)

### 1) Entidades: operar sin IO

```python
from uuid import uuid4

from app.domain.entities import Document

doc = Document(id=uuid4(), title="Manual")
doc.mark_deleted()
assert doc.is_deleted

doc.restore()
assert not doc.is_deleted
```

### 2) Políticas: lectura según visibilidad/ACL

```python
from uuid import UUID, uuid4

from app.domain.entities import Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor, can_read_workspace
from app.identity.users import UserRole

ws = Workspace(id=uuid4(), name="Legal", visibility=WorkspaceVisibility.SHARED, owner_user_id=uuid4())
actor = WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.EMPLOYEE)

allowed = can_read_workspace(ws, actor, shared_user_ids=[actor.user_id])
print(allowed)
```

### 3) Normalización: roles y tags desde metadata

```python
from app.domain.access import normalize_allowed_roles
from app.domain.tags import normalize_tags

metadata = {
    "allowed_roles": ["admin", "EMPLOYEE", None, "  ", "otro"],
    "tags": ["manual", " manual ", "", None, "pdf"],
}

allowed_roles = normalize_allowed_roles(metadata)
tags = normalize_tags(metadata)
print(allowed_roles, tags)
```

### 4) Puertos: stubs para tests de Application

```python
from typing import Protocol
from uuid import UUID

from app.domain.entities import Workspace

class WorkspaceRepository(Protocol):
    def get_workspace(self, workspace_id: UUID) -> Workspace | None: ...

class InMemoryWorkspaceRepo:
    def __init__(self):
        self._items: dict[UUID, Workspace] = {}

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return self._items.get(workspace_id)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nueva entidad** (`entities.py`):
   - agregá campos mínimos y métodos que mantengan coherencia (soft-delete, archivado, etc.).
   - evitá meter lógica de IO o dependencias externas.

2. **Nuevo objeto de valor** (`value_objects.py`):
   - hacelo `frozen=True, slots=True` si es inmutable.
   - validá invariantes en `__post_init__`.
   - exponé `to_dict()` si va a salir por HTTP.

3. **Nueva policy** (`workspace_policy.py` o archivo nuevo):
   - mantener funciones puras con inputs explícitos.
   - evitar side-effects y evitar leer repos (eso va en Application).

4. **Nuevo normalizador** (`access.py`/`tags.py` o archivo nuevo):
   - documentá formatos aceptados.
   - devolvé valores estables (orden estable, sin duplicados).

5. **Nuevo puerto** (Protocol):
   - persistencia → `repositories.py` (separar por agregado para cumplir ISP).
   - servicios externos → `services.py`.
   - cache de embeddings → `cache.py`.

6. **API pública del dominio** (`__init__.py`):
   - re-exportar solo símbolos estables (lo que otros módulos deberían importar).

7. **Tests del dominio**:
   - ubicar pruebas puras en `apps/backend/tests/unit/domain/` (ej. `test_workspace_policy.py`, `test_domain_entities.py`).

## 🆘 Troubleshooting

- **Imports profundos por todo el proyecto** → faltan re-exports → revisar `domain/__init__.py` y exponer símbolos estables.
- **`can_read_workspace` devuelve `False` inesperado** → actor `None` o `role=None` → revisar creación de `WorkspaceActor` y el test `tests/unit/domain/test_workspace_policy.py`.
- **Workspace SHARED permite/deniega mal** → `shared_user_ids` no llega (repo ACL vacío o no inyectado) → revisar `WorkspaceAclRepository` (contrato) y el use case que construye la lista.
- **`allowed_roles` termina vacío** → metadata mal formada o con roles no válidos → revisar `normalize_allowed_roles` en `access.py` y `identity/users.py`.
- **Tags duplicados o con espacios** → normalización insuficiente en el origen → revisar `normalize_tags` (`tags.py`) y asegurar que se use antes de persistir.
- **Application depende de infraestructura por accidente** → imports cruzados (`infrastructure` dentro de `domain`) → mover el contrato a `repositories.py`/`services.py` y dejar implementación en Infrastructure.
- **Protocol “crece” sin cohesión** → un repositorio mezcla métodos de varios agregados → dividir en varios Protocols en `repositories.py` (ISP) y ajustar inyección.
- **Errores por incompatibilidad de firma entre Protocol e implementación** → la implementación no cumple el contrato → revisar type hints en `repositories.py`/`services.py` y ajustar la clase en `app/infrastructure/**`.

## 🔎 Ver también

- `../application/README.md` (orquestación de casos de uso)
- `../identity/README.md` (usuarios, roles y actor)
- `../interfaces/README.md` (adaptación a HTTP)
- `../infrastructure/README.md` (implementaciones concretas de los puertos)
- `../container.py` (composición e inyección de dependencias)
- `../../tests/unit/domain/` (tests del dominio)
