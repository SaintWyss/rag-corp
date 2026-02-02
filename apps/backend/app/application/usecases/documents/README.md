# Use Cases: Documents

## 🎯 Misión
Gestionar operaciones de documentos (lectura, listado, actualización, borrado) y compartir resultados/errores tipados comunes.

**Qué SÍ hace**
- Permite listar y obtener documentos con policy de acceso.
- Actualiza metadata y elimina documentos (soft delete).
- Define errores/resultados comunes para documentos y RAG.

**Qué NO hace**
- No define storage o DB concreta (usa repositorios del dominio).
- No expone endpoints HTTP.

**Analogía (opcional)**
- Es el “catálogo” que gestiona los documentos del sistema.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de casos de uso y resultados. |
| 🐍 `delete_document.py` | Archivo Python | Soft delete de documentos. |
| 🐍 `document_results.py` | Archivo Python | Resultados y errores tipados (DocumentError). |
| 🐍 `download_document.py` | Archivo Python | Descarga de contenido desde storage. |
| 🐍 `get_document.py` | Archivo Python | Obtención de documento por ID. |
| 🐍 `list_documents.py` | Archivo Python | Listado con paginación/filters. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `update_document_metadata.py` | Archivo Python | Actualización de metadata/tags/roles. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: DTOs con `workspace_id`, `document_id` y `actor`.
- **Proceso**: policy de workspace + repositorio + normalización de metadata.
- **Output**: `*Result` con documento(s) o error tipado.

Tecnologías/librerías usadas aquí:
- dataclasses/typing; dependencias externas vía puertos.

Flujo típico:
- `ListDocumentsUseCase` aplica access control y retorna lista.
- `GetDocumentUseCase` valida acceso y devuelve entidad.
- `DownloadDocumentUseCase` usa storage para bytes.

## 🔗 Conexiones y roles
- Rol arquitectónico: Application (Use Cases).
- Recibe órdenes de: Interfaces HTTP (`routers/documents.py`).
- Llama a: DocumentRepository, WorkspaceRepository y FileStoragePort.
- Contratos y límites: sin SQL ni FastAPI; solo puertos del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.container import get_get_document_use_case

use_case = get_get_document_use_case()
result = use_case.execute(
    document_id=uuid4(),
    workspace_id=uuid4(),
    actor=None,
)
```

## 🧩 Cómo extender sin romper nada
- Reutiliza `document_results.py` para errores comunes.
- Aplica `resolve_workspace_for_read/write` para acceso consistente.
- Mantén soft delete (no borres físicamente sin cambiar repositorios).
- Exporta el nuevo caso de uso en `documents/__init__.py`.

## 🆘 Troubleshooting
- Síntoma: `NOT_FOUND` en documentos existentes → Causa probable: workspace incorrecto → Mirar `workspace_id` en input.
- Síntoma: metadata no se actualiza → Causa probable: normalización → Mirar `update_document_metadata.py`.
- Síntoma: descarga falla → Causa probable: storage_key faltante → Mirar `download_document.py`.

## 🔎 Ver también
- [Use cases](../README.md)
- [Infrastructure storage](../../../infrastructure/storage/README.md)
- [Document repository](../../../infrastructure/repositories/README.md)
