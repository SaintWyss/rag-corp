# Use Cases: Workspace

## 🎯 Misión
Gestionar el ciclo de vida de workspaces: creación, lectura, actualización, publicación, archivado y control de acceso.

**Qué SÍ hace**
- Orquesta operaciones CRUD y de visibilidad de workspaces.
- Aplica políticas de autorización con `WorkspaceActor`.
- Devuelve resultados tipados y errores consistentes.

**Qué NO hace**
- No expone endpoints HTTP.
- No escribe SQL directo ni conoce la infraestructura.

**Analogía (opcional)**
- Es el “administrador de espacios” donde viven los documentos.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de casos de uso de workspace. |
| 🐍 `archive_workspace.py` | Archivo Python | Archivar workspaces (soft). |
| 🐍 `create_workspace.py` | Archivo Python | Crear workspaces con reglas de negocio. |
| 🐍 `get_workspace.py` | Archivo Python | Obtener un workspace con policy de acceso. |
| 🐍 `list_workspaces.py` | Archivo Python | Listar workspaces visibles al actor. |
| 🐍 `publish_workspace.py` | Archivo Python | Publicar/visibilidad del workspace. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `share_workspace.py` | Archivo Python | Compartir workspaces (ACL). |
| 🐍 `update_workspace.py` | Archivo Python | Actualizar metadata del workspace. |
| 🐍 `workspace_access.py` | Archivo Python | Helpers para acceso read/write a workspaces. |
| 🐍 `workspace_results.py` | Archivo Python | DTOs de resultados y errores de workspace. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `*Input` con `workspace_id` y `actor`.
- **Proceso**: validaciones + policy (roles/visibilidad) → repositorio.
- **Output**: `WorkspaceResult`/`WorkspaceListResult` o `WorkspaceError`.

Tecnologías/librerías usadas aquí:
- dataclasses/typing; dependencias externas se usan vía puertos.

Flujo típico:
- `CreateWorkspaceUseCase.execute()` valida actor y unicidad.
- `workspace_access.resolve_*` centraliza reglas de acceso.
- `workspace_results.py` estandariza errores (`FORBIDDEN`, `NOT_FOUND`, etc.).

## 🔗 Conexiones y roles
- Rol arquitectónico: Application (Use Cases).
- Recibe órdenes de: Interfaces HTTP (routers/workspaces) y admin routes.
- Llama a: WorkspaceRepository y WorkspaceAclRepository (puertos del dominio).
- Contratos y límites: sin SQL ni FastAPI; solo puertos y políticas.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.application.usecases.workspace.create_workspace import CreateWorkspaceInput
from app.container import get_create_workspace_use_case

use_case = get_create_workspace_use_case()
result = use_case.execute(
    CreateWorkspaceInput(name="Legal", actor=None, owner_user_id=uuid4())
)
```

## 🧩 Cómo extender sin romper nada
- Agrega un nuevo caso de uso en este paquete con DTOs propios.
- Reutiliza `workspace_access` para políticas consistentes.
- Actualiza `workspace_results.py` si incorporas nuevos errores.
- Exporta el caso de uso en `__init__.py` y cablea en `app/container.py`.

## 🆘 Troubleshooting
- Síntoma: `FORBIDDEN` en creación → Causa probable: rol no admin → Mirar `create_workspace.py`.
- Síntoma: `NOT_FOUND` al leer → Causa probable: workspace archivado → Mirar `workspace_access.py`.
- Síntoma: share no surte efecto → Causa probable: ACL repository vacío → Mirar repo en `infrastructure/repositories`.

## 🔎 Ver también
- [Use cases](../README.md)
- [Workspace router](../../../interfaces/api/http/routers/workspaces.py)
- [Domain workspace policy](../../../domain/workspace_policy.py)
