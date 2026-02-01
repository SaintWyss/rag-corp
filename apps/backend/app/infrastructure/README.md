# Infrastructure Layer

Esta capa contiene las **implementaciones concretas** de los puertos definidos en `app/domain`.
Aquí es donde el código "puro" se encuentra con el mundo real (Base de Datos, Servicios Cloud, APIs externas).

## 🎯 Filosofía

- **Plug-and-Play**: Las implementaciones deben ser intercambiables (ej: `PostgresDocumentRepository` vs `InMemoryDocumentRepository`) sin tocar el dominio.
- **Aislamiento de Librerías**: `sqlalchemy`, `boto3`, `google-generativeai`, `redis`, `rq` viven AQUÍ. No deben importarse en `domain/` ni `application/`.
- **Fail-Fast**: Las clases deben validar su configuración (connection strings, API keys) en el `__init__`.

## 📂 Organización

| Módulo      | Responsabilidad                                | Port del Dominio          |
| :---------- | :--------------------------------------------- | :------------------------ |
| `db/`       | Persistencia relacional (Postgres + pgvector). | `repositories.py`         |
| `queue/`    | Procesamiento asíncrono (Redis Queue).         | `DocumentProcessingQueue` |
| `storage/`  | Almacenamiento de archivos (S3 / MinIO).       | `FileStoragePort`         |
| `services/` | Integraciones externas (LLMs, Embeddings).     | `services.py`             |
| `text/`     | Procesamiento de texto (Chunking, Parsing).    | `TextChunkerService`      |
| `cache/`    | Caching de vectores y resultados.              | `EmbeddingCachePort`      |

## 🛠 Patrones Clave

### 1. Repository Pattern

Ocultamos SQL y ORMs detrás de métodos de colección (`save`, `get_by_id`, `find_by_criteria`).
Usamos **PGVector** para búsqueda semántica, encapsulado en queries nativas o helpers.

### 2. Adapter Pattern

Cada clase aquí es un Adaptador que "enchufa" una librería externa a una "toma de corriente" (Protocolo) del dominio.
Ejemplo: `RQDocumentProcessingQueue` adapta la librería `rq` al protocolo `DocumentProcessingQueue`.

### 3. Instrumentation

Los adaptadores deben emitir métricas y logs.
Ejemplo: `InstrumentedConnectionPool` decora el pool de DB para medir tiempos de conexión.

## ⚠️ Reglas de Importación

- ✅ Puede importar: `app.domain`, `app.crosscutting`.
- ❌ NO puede importar: `app.api` (circular dependency), `app.application` (a veces permitido para DTOs, pero evitar si es posible).
