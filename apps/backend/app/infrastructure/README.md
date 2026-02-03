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

- No define reglas de negocio. Razón: ** el negocio pertenece a Domain/Application. Impacto: ** infraestructura no decide permisos, visibilidad ni políticas; si algo debe validarse, se valida arriba.

- No expone endpoints HTTP. Razón: ** el transporte pertenece a _Interfaces_. Impacto: ** routers y DTOs HTTP viven fuera; infraestructura solo ofrece implementaciones que Application consume.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :-------------- | :------------- | :---------------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Facade de exports: re-exporta piezas clave para imports estables desde el container. |
| `cache.py` | Archivo Python | Backend de cache de embeddings (Redis o in-memory) con TTL y hashing de keys. |
| `db` | Carpeta | Pool de conexiones, inicialización/cierre, errores tipados, instrumentación y guardrails de DB. |
| `parsers` | Carpeta | Extractores de texto (PDF/DOCX) y registry que selecciona parser por MIME/type. |
| `prompts` | Carpeta | Loader de prompts versionados con frontmatter (metadatos) y templates para LLM. |
| `queue` | Carpeta | Adapter RQ: enqueue/dequeue jobs, serialización de payloads y configuración de colas. |
| `repositories` | Carpeta | Implementaciones de repositorios: Postgres (psycopg/pgvector) e in-memory para tests/dev. |
| `services` | Carpeta | Adapters a proveedores externos (Google LLM/embeddings, fakes) + retry y caching. |
| `storage` | Carpeta | Adapter S3/MinIO (FileStoragePort) con presigned URLs y errores tipados. |
| `text` | Carpeta | Chunking determinístico (baseline) + variantes semánticas/estructuradas. |
| `README.md` | Documento | Portada + índice de infraestructura (este archivo). |

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
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_document_repository, get_embedding_service
repo = get_document_repository()
emb = get_embedding_service()
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.db.pool import init_pool, close_pool
init_pool(database_url="postgresql://...", min_size=1, max_size=5)
close_pool()
```

```python
# Por qué: deja visible el flujo principal.
from app.infrastructure.queue.job_paths import PROCESS_DOCUMENT_JOB_PATH
print(PROCESS_DOCUMENT_JOB_PATH)
```

## 🧩 Cómo extender sin romper nada
- Definí el puerto en `domain/` si no existe.
- Implementá el adapter en el submódulo correspondiente.
- Tipá errores y evitá filtrar excepciones de vendor.
- Cableá en `app/container.py`.
- Tests: unit para mapping/errores en `apps/backend/tests/unit/`, integration si toca IO real en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `PoolNotInitializedError`.
- **Causa probable:** pool no inicializado.
- **Dónde mirar:** `db/pool.py` y `app/api/main.py`.
- **Solución:** llamar `init_pool()` en startup.
- **Síntoma:** embeddings/LLM no funcionan.
- **Causa probable:** API key faltante o fakes habilitados.
- **Dónde mirar:** `services/README.md` y `crosscutting/config.py`.
- **Solución:** configurar keys o flags.
- **Síntoma:** parser no soporta MIME.
- **Causa probable:** MIME no registrado.
- **Dónde mirar:** `parsers/registry.py`.
- **Solución:** agregar parser/alias.
- **Síntoma:** jobs no se procesan.
- **Causa probable:** worker/Redis caídos.
- **Dónde mirar:** `queue/README.md` y logs del worker.
- **Solución:** levantar servicios.

## 🔎 Ver también
- `./db/README.md`
- `./repositories/README.md`
- `./services/README.md`
- `./storage/README.md`
- `./queue/README.md`
- `./parsers/README.md`
- `./text/README.md`
- `./prompts/README.md`
