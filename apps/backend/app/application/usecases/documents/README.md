# documents
Como un **mostrador de documentos**: aplica permisos y devuelve CRUD con errores tipados.

## 🎯 Misión
Este paquete implementa los casos de uso de documentos dentro de un workspace: listar, obtener, descargar, actualizar metadata y eliminar (soft delete). Centraliza `DocumentError` y resultados compartidos.

### Qué SÍ hace
- Aplica policy de acceso al workspace antes de leer/escribir.
- Normaliza metadata (nombre/tags) y valida inputs defensivos.
- Mantiene soft delete por defecto.
- Devuelve resultados tipados (`DocumentError`, `DocumentErrorCode`).

### Qué NO hace (y por qué)
- No implementa DB ni storage concretos.
  - Razón: se usa puertos del dominio.
  - Consecuencia: infra se inyecta desde `container.py`.
- No expone HTTP.
  - Razón: el transporte vive en `interfaces/`.
  - Consecuencia: los routers solo adaptan.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del bounded context Documents. |
| `__init__.py` | Archivo Python | Exports públicos de documentos. |
| `document_results.py` | Archivo Python | Resultados y errores tipados compartidos. |
| `list_documents.py` | Archivo Python | Listado por workspace con filtros defensivos. |
| `get_document.py` | Archivo Python | Obtiene metadata de un documento. |
| `download_document.py` | Archivo Python | Resuelve descarga vía FileStoragePort. |
| `update_document_metadata.py` | Archivo Python | Actualiza nombre/tags con validación. |
| `delete_document.py` | Archivo Python | Soft delete del documento. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Acceso**: todos los casos de uso llaman `resolve_workspace_for_read` o `resolve_workspace_for_write`.
- **Listado**: aplica límites defensivos de paginación y orden estable (según repo).
- **Metadata**: `update_document_metadata` exige al menos un campo y reemplaza tags.
- **Download**: delega a `FileStoragePort` usando `storage_key`.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Application (documents).
- **Recibe órdenes de:** routers HTTP (documents) y worker (si aplica).
- **Llama a:** `DocumentRepository`, `WorkspaceRepository`, `FileStoragePort`.
- **Reglas de límites:** sin SQL ni SDKs directos; errores tipados para RFC7807.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.container import get_get_document_use_case

use_case = get_get_document_use_case()
result = use_case.execute(document_id="...", workspace_id="...", actor=None)
```

```python
from app.container import get_list_documents_use_case

use_case = get_list_documents_use_case()
result = use_case.execute(workspace_id="...", actor=None, limit=20, offset=0)
```

```python
from app.container import get_download_document_use_case

use_case = get_download_document_use_case()
result = use_case.execute(document_id="...", workspace_id="...", actor=None)
```

## 🧩 Cómo extender sin romper nada
- Reutilizá `document_results.py` para errores/resultados nuevos.
- Usá helpers de acceso en `workspace_access.py`.
- Si necesitás IO nuevo, agregá puerto en `domain/` e implementación en `infrastructure/`.
- Cableá en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/application/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `NOT_FOUND` con documento existente.
  - **Causa probable:** `workspace_id` incorrecto o sin acceso.
  - **Dónde mirar:** `workspace_access.py`.
  - **Solución:** revisar actor y scope.
- **Síntoma:** metadata no se actualiza.
  - **Causa probable:** campos inválidos o vacíos.
  - **Dónde mirar:** `update_document_metadata.py`.
  - **Solución:** enviar `name`/`tags` válidos.
- **Síntoma:** download falla.
  - **Causa probable:** `storage_key` ausente o storage no configurado.
  - **Dónde mirar:** `download_document.py` y `container.py`.
  - **Solución:** corregir storage y metadata.
- **Síntoma:** delete “no borra”.
  - **Causa probable:** es soft delete por diseño.
  - **Dónde mirar:** `delete_document.py`.
  - **Solución:** validar estado o crear purge explícito.

## 🔎 Ver también
- `../README.md`
- `../workspace/workspace_access.py`
- `../../../infrastructure/storage/README.md`
- `../../../infrastructure/repositories/README.md`
