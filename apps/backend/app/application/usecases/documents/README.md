# Feature: Documents Management

## 🎯 Misión

Gestiona las operaciones CRUD básicas sobre los documentos ya existentes.
Se encarga de la visualización, listado y eliminación segura.

**Qué SÍ hace:**

- Listado paginado de documentos en un workspace.
- Descarga del archivo original.
- Edición de metadatos (título, tags).
- Eliminación (Soft Delete).

**Qué NO hace:**

- No procesa contenido (eso es `ingestion`).

## 🗺️ Mapa del territorio

| Recurso                       | Tipo       | Responsabilidad (en humano)                       |
| :---------------------------- | :--------- | :------------------------------------------------ |
| `delete_document.py`          | 🐍 Archivo | Marca un documento como eliminado (`deleted_at`). |
| `document_results.py`         | 🐍 Archivo | DTOs de respuesta para listados.                  |
| `download_document.py`        | 🐍 Archivo | Genera URL firmada o stream bytes para descargar. |
| `get_document.py`             | 🐍 Archivo | Obtiene un documento individual.                  |
| `list_documents.py`           | 🐍 Archivo | Lista documentos con filtros y paginación.        |
| `update_document_metadata.py` | 🐍 Archivo | Cambia nombre o metadatos.                        |

## ⚙️ ¿Cómo funciona por dentro?

Operaciones CRUD estándar contra el `DocumentRepository`.
La eliminación es lógica (**Soft Delete**): los datos no se borran físicamente para mantener integridad referencial y auditoría, solo se marcan como no visibles.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Use Cases (Document CRUD).
- **Colabora con:** `DocumentRepository`.

## 👩‍💻 Guía de uso (Snippets)

### Listar documentos

```python
use_case = ListDocumentsUseCase(repo)
docs = use_case.execute(
    workspace_id=ws_id,
    page=1,
    page_size=20
)
```

## 🧩 Cómo extender sin romper nada

1.  **Filtros:** Si quieres filtrar por "Fecha de creación", agrega el campo al DTO de entrada en `list_documents.py` y actualiza el repositorio.

## 🆘 Troubleshooting

- **Síntoma:** Error "Document not found" al intentar borrar.
  - **Causa:** El documento ya estaba borrado (soft delete) o no pertenece al workspace.

## 🔎 Ver también

- [Ingesta (Creación de documentos)](../ingestion/README.md)
