# in_memory
Como una **libreta temporal**: guarda datos en RAM para tests/dev y se borra al reiniciar el proceso.

## 🎯 Misión

Este módulo provee implementaciones **in‑memory** de repositorios del dominio para **unit tests**, desarrollo local y escenarios donde no querés levantar Postgres. Mantiene las **mismas firmas** (Protocols) que consume Application, pero reemplaza SQL por estructuras Python.

El foco acá es: **rapidez**, **determinismo** (orden estable para tests) y **paridad razonable** con los repos Postgres en lo que los casos de uso necesitan (sin intentar simular un motor SQL).

Recorridos rápidos por intención:

* **Quiero un repo de conversación con historial acotado** → `conversation.py`
* **Quiero workspaces en memoria con orden estable** → `workspace.py`
* **Quiero ACL en memoria (shared users) + reverse lookup** → `workspace_acl.py`
* **Quiero auditar respuestas sin DB (dict simple)** → `audit_repository.py`
* **Quiero votos/feedback por conversación/mensaje (idempotente)** → `feedback_repository.py`
* **Quiero ver cómo se exportan/agrupan los repos** → `__init__.py`

### Qué SÍ hace

* Implementa repositorios en memoria para conversación, workspaces, ACL y feedback/auditoría.
* Permite tests rápidos sin DB y sin I/O.
* Devuelve tipos y estructuras compatibles con los contratos que usa Application.
* En algunos repos, agrega protecciones típicas de tests: **thread‑safety** con `Lock`, ordenamiento determinístico y copias defensivas.

### Qué NO hace (y por qué)

* No persiste datos entre procesos.

- **Razón:** todo vive en RAM.
- **Impacto:** reiniciar el proceso (o reinstanciar el repo) borra el estado; los tests deben crear su propio setup.
* No reemplaza Postgres en producción.

- **Razón:** no hay garantías de durabilidad, concurrencia real, índices, constraints ni performance bajo carga.
- **Impacto:** su uso está limitado a tests/dev; en runtime real se inyectan repos Postgres desde el Container.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :----------------------- | :------------- | :------------------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Exporta repositorios in‑memory para imports estables desde `repositories.in_memory`. |
| `audit_repository.py` | Archivo Python | Auditoría en memoria (dict) para tests/dev; permite listar y filtrar registros. |
| `conversation.py` | Archivo Python | Conversaciones en memoria (dict → `deque(maxlen)`), append-only y thread-safe con `Lock`. |
| `feedback_repository.py` | Archivo Python | Votos/feedback en memoria con idempotencia por (conversación, mensaje, usuario). |
| `workspace.py` | Archivo Python | Workspaces en memoria: CRUD mínimo, archivado soft y listados con orden determinístico. |
| `workspace_acl.py` | Archivo Python | ACL en memoria por workspace (lista sin duplicados) + reverse lookup user→workspaces; thread-safe. |
| `README.md` | Documento | Portada + guía operativa del paquete in‑memory. |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output usando estructuras Python.

### 1) Conversaciones (`conversation.py`)

* **Input:** `conversation_id` + `ConversationMessage`.
* **Proceso:**

- Guarda el historial por conversación en `deque(maxlen=N)`.
- `append_message(...)` hace upsert: si no existe la conversación, la crea.
- `get_messages(..., limit)` devuelve tail de los últimos N si pedís `limit>0`.
- Protege todas las operaciones con `Lock` (thread‑safe para tests concurrentes).
* **Output:** lista de mensajes del dominio.

Detalle importante:

* `max_messages` es un guard rail: evita crecimiento infinito del historial en tests.

### 2) Workspaces (`workspace.py`)

* **Input:** operaciones CRUD y listados desde use cases.
* **Proceso:**

- Mantiene una “tabla” `UUID → Workspace`.
- Devuelve orden determinístico alineado con el repositorio Postgres: **created_at DESC (NULLS LAST) + name ASC**.
- Implementa archivado soft setenado `archived_at`.
- Usa **copias defensivas** para listas mutables (ej. `allowed_roles`, `shared_user_ids`) y para evitar que el caller mutile el estado interno.
- Usa `Lock` para thread‑safety.
* **Output:** `Workspace` del dominio o `None`.

Nota de paridad:

* `list_workspaces_visible_to_user(...)` replica un contrato mínimo sin “política completa”: owner/ORG_READ/SHARED (usando `Workspace.shared_user_ids` en memoria).

### 3) ACL de workspace (`workspace_acl.py`)

* **Input:** `workspace_id` + lista de `user_ids`.
* **Proceso:**

- Guarda ACL como `workspace_id → [user_id, ...]` sin duplicados (dedupe preservando orden).
- `list_workspaces_for_user(...)` hace reverse lookup recorriendo el dict (O(n), aceptable en tests) y ordena por `str(UUID)` para estabilidad.
- Thread‑safe con `Lock`.
* **Output:** listas de UUID (users o workspaces).

### 4) Feedback (`feedback_repository.py`)

* **Input:** `conversation_id`, `message_index`, `user_id`, `vote` (+ comment/tags).
* **Proceso:**

- Genera `vote_id` y guarda un registro en dict.
- Mantiene un índice `conversation:message -> {user_id: vote_id}` para hacer **idempotente** el voto por usuario/mensaje.
- `count_votes(...)` es una implementación simplificada (cuenta por tipo); no modela constraints de DB.
* **Output:** `vote_id` o dict con el voto.

### 5) Auditoría (`audit_repository.py`)

* **Input:** datos de auditoría (record_id, timestamps, user/workspace, resumen, etc.).
* **Proceso:**

- Guarda records en dict y permite listarlos con filtros básicos.
- Marca `is_high_risk` con una heurística simple (por nivel de confianza o cantidad de fuentes).
* **Output:** dicts (no entidades) para tests/dev.

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Infrastructure adapter (testing/dev).

* **Recibe órdenes de:**

- Application (use cases) cuando el Container inyecta repos in‑memory.
- Tests unitarios/integración (setup rápido sin DB).

* **Llama a:**

- Nada externo: solo stdlib (dict/deque/Lock).

* **Reglas de límites (imports/ownership):**

- Debe respetar los Protocols del dominio (`app/domain/repositories.py`).
- No debe importar FastAPI/HTTP.
- No debe ejecutar reglas de negocio (políticas/permisos) más allá de lo mínimo requerido por contratos de tests.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.infrastructure.repositories.in_memory import InMemoryConversationRepository
repo = InMemoryConversationRepository(max_messages=10)
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.repositories.in_memory import InMemoryWorkspaceRepository
repo = InMemoryWorkspaceRepository()
```

```python
# Por qué: deja visible el flujo principal.
from app.infrastructure.repositories.in_memory import InMemoryWorkspaceAclRepository
repo = InMemoryWorkspaceAclRepository()
```

## 🧩 Cómo extender sin romper nada
- Mantener paridad de firmas con `domain/repositories.py`.
- Evitar estado global compartido en tests.
- Cablear selección en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/`, integration para paridad básica.

## 🆘 Troubleshooting
- **Síntoma:** “perdí el estado”.
- **Causa probable:** repo reinstanciado.
- **Dónde mirar:** fixtures de tests.
- **Solución:** crear setup por test.
- **Síntoma:** orden inestable.
- **Causa probable:** falta sort determinístico.
- **Dónde mirar:** repos in-memory.
- **Solución:** ordenar por criterios estables.
- **Síntoma:** ACL con duplicados.
- **Causa probable:** dedupe ausente.
- **Dónde mirar:** `workspace_acl.py`.
- **Solución:** deduplicar preservando orden.
- **Síntoma:** divergencia con Postgres.
- **Causa probable:** métodos no alineados.
- **Dónde mirar:** `postgres/` vs `in_memory/`.
- **Solución:** mantener contratos sincronizados.

## 🔎 Ver también
- `../README.md`
- `../postgres/README.md`
- `../../../domain/repositories.py`
