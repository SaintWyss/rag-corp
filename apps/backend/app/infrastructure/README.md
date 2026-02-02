# Layer: Infrastructure (Adapters)

## 🎯 Misión

Esta capa contiene los **detalles técnicos** y las implementaciones concretas de los contratos definidos en el Dominio.
Aquí es donde la aplicación "toca tierra": se conecta a bases de datos, llama a APIs externas, escribe en disco, etc.

**Qué SÍ hace:**

- Implementa Repositorios (`postgres`, `in_memory`).
- Implementa Servicios de Dominio (`llm`, `storage`, `queue`).
- Maneja drivers de base de datos (`psycopg`).
- Parsea documentos (`pdf`, `docx`).

**Qué NO hace:**

- No define reglas de negocio.
- No decide la lógica de orquestación.

**Analogía:**
Si el Dominio es el "Arquitecto" que diseña la casa, la Infraestructura son los "Albañiles, Electricistas y Plomeros" que la construyen con materiales reales.

## 🗺️ Mapa del territorio

| Recurso         | Tipo       | Responsabilidad (en humano)                               |
| :-------------- | :--------- | :-------------------------------------------------------- |
| `cache.py`      | 🐍 Archivo | Implementación de caché (Redis/Memory).                   |
| `db/`           | 📁 Carpeta | Configuración del Pool de conexiones SQL.                 |
| `parsers/`      | 📁 Carpeta | Extractores de texto para diferentes formatos de archivo. |
| `prompts/`      | 📁 Carpeta | Cargador de templates de prompts desde disco.             |
| `queue/`        | 📁 Carpeta | Adaptador para colas de tareas (RQ).                      |
| `repositories/` | 📁 Carpeta | Implementaciones de persistencia (Postgres/Memory).       |
| `services/`     | 📁 Carpeta | Implementaciones de servicios externos (LLM, Embedding).  |
| `storage/`      | 📁 Carpeta | Almacenamiento de archivos binarios (S3/MinIO/Local).     |
| `text/`         | 📁 Carpeta | Algoritmos de Chunking y procesamiento de texto.          |

## ⚙️ ¿Cómo funciona por dentro?

Patrón **Adapter**.
Cada clase aquí implementa una interfaz (Protocol) definida en `app.domain` o `app.application`.
La inyección de dependencia se resuelve en `app.container` (Composition Root).

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapters (Hexagon Outside).
- **Recibe órdenes de:** `application` (vía interfaces).
- **Llama a:** Bases de Datos, APIs externas (Google, AWS), Sistema de Archivos.

## 👩‍💻 Guía de uso (Snippets)

### Uso típico (Inyección)

Las clases de infra no suelen usarse directamente, se inyectan.

```python
# En app/container.py
from app.infrastructure.repositories.postgres.document import PostgresDocumentRepository

def get_document_repository() -> DocumentRepository:
    return PostgresDocumentRepository()
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevo adaptador:** Si quieres cambiar Postgres por Mongo, crea `infrastructure/repositories/mongo/` e implementa la misma interfaz del dominio.
2.  **No importes infra en dominio:** Regla de oro. El dominio no puede saber que existe este directorio.

## 🆘 Troubleshooting

- **Síntoma:** Error de conexión a DB/Redis.
  - **Causa:** Configuración de entorno incorrecta (`.env`). Revisa `db/` o `queue/`.
- **Síntoma:** `ImportError` desde dominio.
  - **Causa:** Violación de arquitectura. El dominio está importando infraestructura.

## 🔎 Ver también

- [Repositorios (Persistencia)](./repositories/README.md)
- [Base de Datos (Conexión)](./db/README.md)
