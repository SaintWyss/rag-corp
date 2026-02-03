# Infrastructure (adaptadores)

Como una **ferretería del backend**: acá están las implementaciones concretas (DB, storage, colas, parsers, IA) que el resto del sistema usa sin ver SDKs ni detalles técnicos.

## 🎯 Misión

`infrastructure/` contiene los **adapters concretos** que implementan los puertos del dominio (repositorios, storage, servicios de IA, colas, parsers y utilidades de texto). Es el lugar donde vive el código que habla con Postgres/pgvector, Redis/RQ, S3/MinIO y proveedores de LLM/embeddings.

Este README funciona como **portada + índice**: describe qué hace la capa y te lleva al submódulo correcto según lo que estés intentando entender o modificar.

Recorridos rápidos por intención:

- **Quiero DB (pool, timeouts, guardrails, errores)** → `./db/README.md`
- **Quiero repositorios Postgres / in-memory (puertos del dominio)** → `./repositories/README.md`
- **Quiero storage S3/MinIO (upload/download/presign + errores tipados)** → `./storage/README.md`
- **Quiero colas (enqueue jobs del worker)** → `./queue/README.md`
- **Quiero parsers/extractores (PDF/DOCX y registry por MIME)** → `./parsers/README.md`
- **Quiero LLM/embeddings + retry + cache** → `./services/README.md`
- **Quiero chunking de texto (baseline/semántico/estructurado)** → `./text/README.md`
- **Quiero prompts versionados con frontmatter** → `./prompts/README.md`
- **Quiero entender el wiring (qué implementación se usa en runtime)** → `../container.py`

### Qué SÍ hace

- Provee implementaciones reales de los puertos del dominio:
  - repositorios (Postgres / in-memory)
  - storage (S3/MinIO)
  - cola (RQ sobre Redis)
  - servicios externos (LLM/embeddings)
  - parsers/extractores de texto (PDF/DOCX)
  - utilidades de texto (chunking)

- Encapsula SDKs y detalles técnicos:
  - manejo de credenciales, endpoints, timeouts
  - retries, cache-aside, batch limits
  - tipado de errores y observabilidad asociada

### Qué NO hace (y por qué)

- No define reglas de negocio.
  - **Razón:** el negocio pertenece a Domain/Application.
  - **Impacto:** infraestructura no decide permisos, visibilidad ni políticas; si algo debe validarse, se valida arriba.

- No expone endpoints HTTP.
  - **Razón:** el transporte pertenece a _Interfaces_.
  - **Impacto:** routers y DTOs HTTP viven fuera; infraestructura solo ofrece implementaciones que Application consume.

## 🗺️ Mapa del territorio

| Recurso         | Tipo           | Responsabilidad (en humano)                                                                     |
| :-------------- | :------------- | :---------------------------------------------------------------------------------------------- |
| `__init__.py`   | Archivo Python | Facade de exports: re-exporta piezas clave para imports estables desde el container.            |
| `cache.py`      | Archivo Python | Backend de cache de embeddings (Redis o in-memory) con TTL y hashing de keys.                   |
| `db/`           | Carpeta        | Pool de conexiones, inicialización/cierre, errores tipados, instrumentación y guardrails de DB. |
| `parsers/`      | Carpeta        | Extractores de texto (PDF/DOCX) y registry que selecciona parser por MIME/type.                 |
| `prompts/`      | Carpeta        | Loader de prompts versionados con frontmatter (metadatos) y templates para LLM.                 |
| `queue/`        | Carpeta        | Adapter RQ: enqueue/dequeue jobs, serialización de payloads y configuración de colas.           |
| `repositories/` | Carpeta        | Implementaciones de repositorios: Postgres (psycopg/pgvector) e in-memory para tests/dev.       |
| `services/`     | Carpeta        | Adapters a proveedores externos (Google LLM/embeddings, fakes) + retry y caching.               |
| `storage/`      | Carpeta        | Adapter S3/MinIO (FileStoragePort) con presigned URLs y errores tipados.                        |
| `text/`         | Carpeta        | Chunking determinístico (baseline) + variantes semánticas/estructuradas.                        |
| `README.md`     | Documento      | Portada + índice de infraestructura (este archivo).                                             |

## ⚙️ ¿Cómo funciona por dentro?

Infraestructura funciona como “capa de traducción” entre el mundo del dominio y el mundo real (IO).

### Input → Proceso → Output

- **Input:** llamadas desde casos de uso (Application) a través de puertos del dominio.
- **Proceso:** cada adapter traduce esa intención a una operación concreta:
  - SQL/tx sobre Postgres
  - comandos RQ sobre Redis
  - requests S3 (put/get/delete, presign)
  - llamadas a SDKs de IA (Google GenAI)
  - parsing de archivos (PDF/DOCX)

- **Output:** entidades/DTOs de dominio, datos persistidos, respuestas de proveedores o errores tipados.

### Flujos típicos (recorridos end-to-end)

#### 1) Ingesta de documento subido

1. Application (`UploadDocumentUseCase`) pide a **storage** subir bytes → `storage/`.
2. Persiste metadata en **repositorios** → `repositories/postgres/`.
3. Encola el procesamiento en **queue** → `queue/`.
4. Worker consume el job y descarga el archivo desde **storage**.
5. Parser en `parsers/` extrae texto según MIME.
6. `text/` parte en chunks.
7. `services/` genera embeddings (Google/Fake + cache/retry).
8. `repositories/postgres/` guarda chunks + embeddings (pgvector).

#### 2) Query/Answering (RAG)

1. Application pide embeddings de la query → `services/`.
2. Repositorio Postgres hace vector search/MMR → `repositories/postgres/document.py`.
3. Application arma contexto y llama LLM → `services/llm/`.

#### 3) Administración de workspaces

1. Application usa repositorios de workspace/ACL → `repositories/`.
2. Auditoría (si existe) se persiste en repositorio audit → `repositories/postgres/audit_event.py`.

### Tecnologías usadas (por subsistema)

- DB/Repos: `psycopg`, `pgvector`, SQL parametrizado.
- Queue: `redis`, `rq`.
- Storage: `boto3`/`botocore` (S3/MinIO).
- IA: `google-genai`.
- Parsers: `pypdf` (PDF), `python-docx` (DOCX).

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Infrastructure_ (adapters de IO).

- **Recibe órdenes de:**
  - _Application_ (use cases) en runtime.
  - _Worker_ (jobs) durante ejecución asíncrona.

- **Llama a:**
  - Postgres
  - Redis
  - S3/MinIO
  - proveedores de IA

- **Reglas de límites (imports/ownership):**
  - Infraestructura no debe contener reglas de negocio.
  - Infraestructura no conoce HTTP ni DTOs de transporte.
  - Las decisiones de “qué implementación usar” pertenecen al container (`../container.py`).

## 👩‍💻 Guía de uso (Snippets)

### 1) DB pool (patrón de arranque/cierre)

```python
from app.infrastructure.db.pool import init_pool, close_pool

pool = init_pool(
    database_url="postgresql://...",
    min_size=1,
    max_size=5,
)

# ... usar repositorios que dependan del pool ...

close_pool()
```

### 2) Obtener implementations desde el container (runtime)

```python
from app.container import (
    get_document_repository,
    get_file_storage,
    get_document_queue,
    get_embedding_service,
    get_llm_service,
)

repo = get_document_repository()
storage = get_file_storage()
queue = get_document_queue()
emb = get_embedding_service()
llm = get_llm_service()
```

### 3) Enqueue de un job (cola)

```python
from uuid import UUID

from app.container import get_document_queue

queue = get_document_queue()
queue.enqueue_document_processing(
    document_id=UUID("22222222-2222-2222-2222-222222222222"),
    workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
)
```

### 4) Storage: presigned URL (descarga directa)

```python
from app.container import get_file_storage

storage = get_file_storage()
if storage is None:
    raise RuntimeError("Storage no configurado")

url = storage.generate_presigned_url(
    "documents/222/manual.pdf",
    expires_in_seconds=600,
    filename="manual.pdf",
)
print(url)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico para sumar adapters sin romper wiring ni contratos:

1. **Definir el puerto en Domain** (si no existe).
   - Interface/Protocol con métodos mínimos.

2. **Implementar el adapter en Infrastructure**
   - crear carpeta o archivo dentro del subsistema correcto (`services/`, `storage/`, `queue/`, etc.).
   - usar SQL parametrizado / SDK encapsulado / lazy imports cuando sea opcional.

3. **Errores tipados y trazabilidad**
   - traducir errores de vendor a errores del subsistema (sin filtrar tipos externos).
   - mantener `raise ... from exc` para preservar causa.

4. **Cablear en el container**
   - agregar getters en `../container.py`.
   - resolver selección por settings/feature flags.

5. **Tests**
   - unit: mocks/fakes para ramas de error.
   - integration: si toca recursos reales (DB/Redis/MinIO), agregar tests con servicios locales.

6. **Documentación**
   - agregar/actualizar el README del submódulo.
   - linkear desde este README en “Ver también”.

## 🆘 Troubleshooting

1. **`PoolNotInitializedError`**

- Causa probable: DB pool no inicializado en startup.
- Dónde mirar: `./db/pool.py` + entrypoints (API/worker) donde se llama `init_pool()`.
- Solución: inicializar pool al arrancar y cerrarlo al apagar.

2. **Embeddings/LLM no funcionan**

- Causa probable: `GOOGLE_API_KEY` faltante o flags `fake_*` activados.
- Dónde mirar: `./services/README.md` y `../crosscutting/config.py`.
- Solución: setear API key, revisar `Settings.fake_embeddings` / `Settings.fake_llm`.

3. **Parser falla para un MIME**

- Causa probable: registry sin parser para ese tipo o librería faltante.
- Dónde mirar: `./parsers/registry.py` + `./parsers/README.md`.
- Solución: registrar un parser para el MIME o instalar dependencia (`pypdf`, `python-docx`).

4. **Uploads fallan (S3/MinIO)**

- Causa probable: credenciales/bucket/endpoint incorrectos.
- Dónde mirar: `./storage/README.md`.
- Solución: revisar settings `s3_*`, conectividad al endpoint y permisos.

5. **Jobs no se procesan**

- Causa probable: worker apagado o Redis inaccesible.
- Dónde mirar: `./queue/README.md` y logs del worker.
- Solución: levantar Redis/worker y validar `REDIS_URL`.

6. **Vector search da 0 resultados**

- Causa probable: embeddings/dimensión desalineada o scope incorrecto.
- Dónde mirar: `./repositories/postgres/README.md`.
- Solución: validar dimensión (`768`), migraciones pgvector y `workspace_id` en queries.

## 🔎 Ver también

- `./db/README.md` (pool, guardrails y errores de DB)
- `./repositories/README.md` (repositorios Postgres/in-memory)
- `./services/README.md` (LLM/embeddings, retry y caching)
- `./storage/README.md` (S3/MinIO + presigned URLs)
- `./queue/README.md` (RQ/Redis, jobs del worker)
- `./parsers/README.md` (extractores de texto y registry por MIME)
- `./text/README.md` (chunking y fragmentos)
- `./prompts/README.md` (prompts versionados)
- `../container.py` (wiring y selección de implementaciones)
