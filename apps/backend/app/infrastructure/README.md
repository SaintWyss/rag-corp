# Infrastructure (adaptadores)

## 🎯 Misión
Implementar los adaptadores concretos del backend: DB, repositorios, storage, colas, parsers, LLMs y utilidades de texto.

**Qué SÍ hace**
- Provee implementaciones reales de los puertos del dominio.
- Conecta con Postgres, Redis, S3 y proveedores de IA.
- Encapsula detalles técnicos fuera de la capa de aplicación.

**Qué NO hace**
- No define reglas de negocio (eso está en Application/Domain).
- No expone endpoints HTTP.

**Analogía (opcional)**
- Es la “ferretería” donde viven las herramientas concretas.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Facade de exports de infraestructura. |
| 🐍 `cache.py` | Archivo Python | Cache de embeddings (Redis o in‑memory). |
| 📁 `db/` | Carpeta | Pool, errores e instrumentación de DB. |
| 📁 `parsers/` | Carpeta | Extracción de texto (PDF/DOCX) y registry. |
| 📁 `prompts/` | Carpeta | Loader de prompts con frontmatter y versionado. |
| 📁 `queue/` | Carpeta | Adapter RQ para encolar jobs. |
| 📄 `README.md` | Documento | Esta documentación. |
| 📁 `repositories/` | Carpeta | Repositorios Postgres e in‑memory. |
| 📁 `services/` | Carpeta | Implementaciones de embeddings y LLM. |
| 📁 `storage/` | Carpeta | Adapter S3/MinIO para archivos. |
| 📁 `text/` | Carpeta | Chunking y modelos de fragmentos de texto. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: llamadas desde casos de uso vía puertos del dominio.
- **Proceso**: adaptadores transforman la llamada en SQL, HTTP, Redis, S3, etc.
- **Output**: datos persistidos, respuestas de proveedores o errores tipados.

Tecnologías/librerías usadas aquí:
- psycopg/pgvector, redis + rq, boto3, google-genai, pypdf/docx.

Flujo típico:
- Un use case llama un repositorio → `repositories/postgres/*` ejecuta SQL.
- Upload llama storage → `storage/s3_file_storage.py` sube bytes.
- Enqueue usa `queue/rq_queue.py` para crear jobs.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter.
- Recibe órdenes de: Application (use cases), Worker.
- Llama a: Postgres, Redis, S3, proveedores LLM/embeddings.
- Contratos y límites: infraestructura no debe contener reglas de negocio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.db.pool import init_pool, close_pool

pool = init_pool(database_url="postgresql://...", min_size=1, max_size=5)
close_pool()
```

## 🧩 Cómo extender sin romper nada
- Implementa nuevos adapters respetando los puertos del dominio.
- Mantén validaciones y manejo de errores tipados.
- Evita side‑effects en imports; usa lazy imports cuando sea opcional.
- Agrega tests de integración si el adapter toca recursos reales.

## 🆘 Troubleshooting
- Síntoma: `PoolNotInitializedError` → Causa probable: no se inicializó pool → Mirar `db/pool.py`.
- Síntoma: embeddings no funcionan → Causa probable: API key o fake enabled → Mirar `services/` y `config`.
- Síntoma: parser falla con un MIME → Causa probable: registry sin parser → Mirar `parsers/registry.py`.

## 🔎 Ver también
- [DB](./db/README.md)
- [Repositories](./repositories/README.md)
- [Services](./services/README.md)
- [Storage](./storage/README.md)
- [Queue](./queue/README.md)
