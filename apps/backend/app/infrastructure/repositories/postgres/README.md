# postgres

Como un **almacén con índice vectorial**: guarda entidades en PostgreSQL y permite recuperar chunks por similitud.

## 🎯 Misión

Este paquete contiene las **implementaciones Postgres** de los repositorios definidos en el dominio. Su trabajo es traducir operaciones del sistema (guardar/listar/buscar) a **SQL parametrizado** sobre PostgreSQL, incluyendo **pgvector** para búsqueda semántica.

Recorridos rápidos por intención:

- **Quiero retrieval (vector search / MMR) y persistencia de documentos + chunks** → `document.py`
- **Quiero CRUD y listados de workspaces (incl. archivado)** → `workspace.py`
- **Quiero ACL de workspaces compartidos** → `workspace_acl.py`
- **Quiero usuarios (auth/admin)** → `user.py`
- **Quiero auditoría (append-only + filtros)** → `audit_event.py`

### Qué SÍ hace

- Persiste documentos, chunks, workspaces, usuarios y auditoría.
- Ejecuta búsqueda vectorial con pgvector (`<=>`) y re-ranking opcional por MMR.
- Mantiene queries determinísticas (orden estable) para que API/tests sean predecibles.

### Qué NO hace (y por qué)

- No define reglas de negocio ni autorización.
  - **Razón:** la policy vive en Domain/Application; el repositorio solo persiste y consulta.
  - **Impacto:** si llamás a estos repos sin haber autorizado arriba, el repo no lo “salva”.

- No expone endpoints HTTP.
  - **Razón:** el transporte pertenece a _Interfaces_.
  - **Impacto:** los routers llaman a casos de uso; los casos de uso llaman a estos repos.

## 🗺️ Mapa del territorio

| Recurso            | Tipo           | Responsabilidad (en humano)                                                                                             |
| :----------------- | :------------- | :---------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`      | Archivo Python | Exporta implementaciones Postgres para imports estables desde `app.container`.                                          |
| `audit_event.py`   | Archivo Python | Guarda y lista eventos de auditoría (append-only) con filtros por actor/acción/fechas y workspace (vía metadata JSONB). |
| `document.py`      | Archivo Python | Persiste documentos + chunks y ejecuta búsqueda vectorial (similitud y MMR) scoped por `workspace_id`.                  |
| `user.py`          | Archivo Python | CRUD de usuarios (auth/admin) + wrapper `PostgresUserRepository` para uso OO consistente.                               |
| `workspace.py`     | Archivo Python | CRUD de workspaces con archivado (soft) y listados determinísticos; incluye “visibles para usuario”.                    |
| `workspace_acl.py` | Archivo Python | ACL de workspaces compartidos: lookup directo/inverso y reemplazo transaccional de permisos.                            |
| `README.md`        | Documento      | Portada + guía de navegación del paquete.                                                                               |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output, con los pasos reales que se repiten en este paquete.

### 1) Pool y ejecución de SQL

- **Input:** llamadas desde casos de uso (Application) o servicios de identidad.
- **Proceso:**
  1. cada repos obtiene un pool con `app.infrastructure.db.pool.get_pool()` (o lo recibe inyectado en tests).
  2. abre conexión con `with pool.connection() as conn:`.
  3. ejecuta SQL **parametrizado** (`%s`, tuplas), sin interpolar input de usuario.
  4. en operaciones atómicas, usa transacciones (`with conn.transaction():`).
  5. mapea filas a entidades (`_row_to_*`) para mantener un contrato estable.

- **Output:** entidades de dominio (ej. `Workspace`, `Document`, `Chunk`, `User`, `AuditEvent`) o tipos simples.

Nota de runtime:

- El pool registra pgvector y aplica `statement_timeout` según `Settings.db_statement_timeout_ms`.

### 2) Documentos + chunks + vector search (`document.py`)

- **Input:** `embedding: list[float]`, `top_k`, `workspace_id` (obligatorio en retrieval).
- **Proceso:**
  - valida dimensión de embeddings (contrato `EMBEDDING_DIMENSION = 768`).
  - exige `workspace_id` como boundary (bloquea cross-scope).
  - ejecuta JOIN `chunks` + `documents`, filtra por `d.deleted_at IS NULL` y por workspace.
  - ordena por distancia (`ORDER BY c.embedding <=> %s::vector`) y calcula `score = 1 - distance`.
  - si se usa MMR: trae candidatos (fetch_k) y re-rankeá localmente con numpy (`_mmr_rerank`).

- **Output:** `list[Chunk]` con `similarity` y contexto del documento (`document_title`, `document_source`).

### 3) Workspaces y visibilidad (`workspace.py`)

- **Input:** filtros (owner, visibility, ids), flags (`include_archived`).
- **Proceso:**
  - queries parametrizadas con orden determinístico.
  - archivado como soft-state (`archived_at`): listados pueden excluir o incluir.
  - listado “visible para usuario” en una query (combina owner, visibilidad y ACL).

- **Output:** `list[Workspace]` o `Workspace | None`.

### 4) ACL compartida (`workspace_acl.py`)

- **Input:** `workspace_id`, lista de `user_ids`.
- **Proceso:**
  - `replace_workspace_acl` corre en transacción: delete total + insert batch con `UNNEST(%s::uuid[])`.
  - lookups directos/inversos con orden estable (útil para tests y UX).

- **Output:** listas de UUIDs o `None` (operaciones de escritura).

### 5) Auditoría (`audit_event.py`)

- **Input:** `AuditEvent` o filtros (workspace, actor, action_prefix, fechas, paginado).
- **Proceso:**
  - `record_event` inserta append-only.
  - `list_events` filtra por `metadata->>'workspace_id'` (workspace se guarda como string en JSONB).

- **Output:** `list[AuditEvent]`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Infrastructure_ (adapter de DB).

- **Recibe órdenes de:**
  - Casos de uso de _Application_ (documents/workspaces/ingestion).
  - Módulos de identidad/autenticación (usuarios).

- **Llama a:**
  - `app.infrastructure.db.pool.get_pool()`.
  - `app.crosscutting.config.get_settings()` (indirectamente, vía pool para timeouts).

- **Reglas de límites (imports/ownership):**
  - No aplica policy (ACL/RBAC/visibilidad) por cuenta propia.
  - No depende de FastAPI ni de DTOs HTTP.
  - No “invoca” servicios externos (solo DB). Si aparece IO extra, pertenece a otro adapter.

## 👩‍💻 Guía de uso (Snippets)

### 1) Uso típico desde runtime (via container)

```python
from uuid import UUID

from app.container import get_document_repository

repo = get_document_repository()
chunks = repo.find_similar_chunks(
    embedding=[0.0] * 768,
    top_k=5,
    workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
)
print(len(chunks))
```

### 2) Vector search con MMR (diversidad)

```python
from uuid import UUID

from app.infrastructure.repositories.postgres.document import PostgresDocumentRepository

repo = PostgresDocumentRepository()
chunks = repo.find_similar_chunks_mmr(
    embedding=[0.0] * 768,
    top_k=5,
    fetch_k=30,
    lambda_mult=0.5,
    workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
)
print([c.similarity for c in chunks])
```

### 3) Inicializar pool en integración (patrón de tests)

```python
from app.crosscutting.config import get_settings
from app.infrastructure.db.pool import init_pool

settings = get_settings()
init_pool(
    database_url=settings.database_url,
    min_size=settings.db_pool_min_size,
    max_size=settings.db_pool_max_size,
)
```

### 4) ACL: reemplazar usuarios compartidos

```python
from uuid import UUID

from app.infrastructure.repositories.postgres import PostgresWorkspaceAclRepository

repo = PostgresWorkspaceAclRepository()
repo.replace_workspace_acl(
    workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
    user_ids=[
        UUID("11111111-1111-1111-1111-111111111111"),
        UUID("22222222-2222-2222-2222-222222222222"),
    ],
)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo repositorio:** crea `foo.py` dentro de este paquete con una clase `PostgresFooRepository`.
2. **Scope y seguridad:**
   - si la entidad es multi-tenant, exigí `workspace_id` en métodos críticos (como `document.py`).

3. **SQL seguro y mantenible:**
   - SQL parametrizado siempre.
   - extraé columnas SELECT a constantes y centralizá mapping (`_row_to_*`).

4. **Transacciones:**
   - operaciones “todo o nada” (replace, batch inserts, delete+insert) deben ser transaccionales.

5. **Cableado:**
   - exportá en `__init__.py`.
   - cableá en `app/container.py` (getter y selección por entorno si aplica).

6. **Migraciones y tests:**
   - agregá migración (Alembic) si hay tablas/columnas nuevas.
   - agregá tests de integración en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting

- **`PoolNotInitializedError` / “Pool no inicializado”** → el proceso no llamó `init_pool()` → mirar `app/api/main.py` (startup) o `tests/integration/conftest.py` → inicializar pool con `Settings.database_url`.
- **Error `UndefinedTable` / “relation does not exist”** → faltan migraciones → correr Alembic (`upgrade head`) y revisar `apps/backend/alembic/`.
- **Error `operator does not exist: vector <=> vector` / `type "vector" does not exist`** → pgvector no instalado → crear extensión `vector` en DB y verificar que el contenedor de DB soporte pgvector.
- **`Query: embedding has X dimensions, expected 768`** → el embedding provider no coincide con el contrato DB → revisar el servicio de embeddings y la tabla `chunks.embedding vector(768)`.
- **`workspace_id is required for find_similar_chunks`** → se está llamando retrieval sin scope → pasar `workspace_id` desde el caso de uso (no “adivinarlo” en el repo).
- **Búsqueda devuelve 0 resultados** → documentos soft-deleted (`deleted_at`) o scope incorrecto → revisar filtros en `document.py` y el `workspace_id` usado.
- **Timeouts en queries** → `statement_timeout` demasiado bajo → ajustar `Settings.db_statement_timeout_ms` y revisar queries/paginado.

## 🔎 Ver también

- `../../db/README.md` (pool, pgvector y guardrails de conexiones)
- `../../../domain/repositories.py` (puertos del dominio)
- `../in_memory/README.md` (implementaciones in-memory para tests/dev)
- `../../../../tests/integration/README.md` (patrones de integración con DB, si existe en el repo)
