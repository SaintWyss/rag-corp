# workspace
Como un **administrador de espacios**: aplica reglas y permisos para crear y gobernar workspaces donde viven los documentos.

## 🎯 Misión

Este módulo reúne los **casos de uso de ciclo de vida de workspaces** (capa *Application*): crear, leer, listar, actualizar, publicar, archivar y compartir, siempre aplicando autorización a través de `WorkspaceActor`.

Recorridos rápidos por intención:

* **Quiero crear un workspace** → `create_workspace.py`
* **Quiero ver uno / listar los visibles** → `get_workspace.py` / `list_workspaces.py`
* **Quiero cambiar visibilidad o estado** → `publish_workspace.py` / `archive_workspace.py`
* **Quiero compartir (ACL)** → `share_workspace.py`
* **Quiero reglas de acceso consistentes** → `workspace_access.py`
* **Quiero DTOs/errores tipados** → `workspace_results.py`

### Qué SÍ hace

* Orquesta operaciones CRUD y de visibilidad sobre workspaces.
* Aplica políticas de autorización con `WorkspaceActor` de forma consistente.
* Devuelve resultados tipados (éxito/error) para que Interfaces adapte a HTTP sin “adivinar”.

### Qué NO hace (y por qué)

* No expone endpoints HTTP.

- **Razón:** el transporte es responsabilidad de *Interfaces*.
- **Impacto:** los routers solo transforman request/response y delegan acá.
* No escribe SQL directo ni conoce la infraestructura.

- **Razón:** mantener Application testeable y desacoplada.
- **Impacto:** todo acceso a datos pasa por repositorios/puertos inyectados desde el container.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :--------------------- | :------------- | :-------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Exporta casos de uso y DTOs para imports estables desde otros módulos. |
| `archive_workspace.py` | Archivo Python | Marca un workspace como archivado y hace cumplir sus reglas de visibilidad. |
| `create_workspace.py` | Archivo Python | Crea workspaces aplicando validaciones y reglas de negocio del sistema. |
| `get_workspace.py` | Archivo Python | Obtiene un workspace verificando acceso del actor (read). |
| `list_workspaces.py` | Archivo Python | Lista workspaces visibles para el actor (según policy y ACL). |
| `publish_workspace.py` | Archivo Python | Cambia el estado de publicación/visibilidad del workspace. |
| `share_workspace.py` | Archivo Python | Gestiona el compartir por ACL (agregar/quitar permisos). |
| `update_workspace.py` | Archivo Python | Actualiza metadata del workspace respetando permisos (write). |
| `workspace_access.py` | Archivo Python | Helpers de acceso read/write: centraliza reglas y evita duplicación entre casos de uso. |
| `workspace_results.py` | Archivo Python | DTOs de resultado y errores tipados para crear/listar/actualizar/compartir. |
| `README.md` | Documento | Portada + guía de navegación del módulo. |

## ⚙️ ¿Cómo funciona por dentro?

Explicación técnica en formato Input → Proceso → Output.

### Patrón común

* **Input:** `*Input` con `workspace_id` (cuando aplica) + `actor` (y payload específico).
* **Proceso:**

  1. validaciones básicas del input.
  2. resolución de acceso con helpers de `workspace_access` (read o write).
  3. ejecución contra repositorios (`WorkspaceRepository`, `WorkspaceAclRepository`).
  4. armado de resultados tipados vía `workspace_results`.
* **Output:** `WorkspaceResult` / `WorkspaceListResult` (o equivalentes) con `data` o `error` tipado.

### Flujos típicos

* **Create:** valida actor y payload, crea el workspace y registra el owner/ACL correspondiente.
* **Get/List:** usa `workspace_access` para filtrar/autorizar y luego carga desde el repositorio.
* **Update/Publish/Archive:** exige permisos de escritura, realiza la transición y devuelve el estado actualizado.
* **Share:** exige permisos de owner/admin (según policy), aplica cambios en ACL y devuelve confirmación/resultados.

## 🔗 Conexiones y roles

* **Rol arquitectónico:** *Application* (Use Cases).

* **Recibe órdenes de:**

- *Interfaces* (routers HTTP) de workspaces y rutas administrativas.

* **Llama a:**

- `WorkspaceRepository` (persistencia de workspace).
- `WorkspaceAclRepository` (permisos y compartición).
- Policy/entidades del dominio (ej. `WorkspaceActor`).

* **Reglas de límites (imports/ownership):**

- Este módulo no conoce FastAPI ni DTOs HTTP.
- No accede a DB directo ni importa implementaciones de infraestructura.
- El cableado de dependencias vive en `app/container.py`.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_create_workspace_use_case
from app.application.usecases.workspace.create_workspace import CreateWorkspaceInput

use_case = get_create_workspace_use_case()
use_case.execute(CreateWorkspaceInput(name="Legal", actor=None, owner_user_id="..."))
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.container import get_list_workspaces_use_case
from app.application.usecases.workspace.list_workspaces import ListWorkspacesInput

use_case = get_list_workspaces_use_case()
use_case.execute(ListWorkspacesInput(actor=None))
```

```python
# Por qué: deja visible el flujo principal.
from app.container import get_share_workspace_use_case
from app.application.usecases.workspace.share_workspace import ShareWorkspaceInput

use_case = get_share_workspace_use_case()
use_case.execute(ShareWorkspaceInput(workspace_id="...", actor=None, target_user_id="...", grant_role="employee"))
```

## 🧩 Cómo extender sin romper nada
- Usá `workspace_access` para validar acceso (read/write) y evitar duplicación.
- Si agregás errores nuevos, tipalos en `workspace_results.py`.
- Cableá el caso de uso en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/application/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `FORBIDDEN` al crear/actualizar.
- **Causa probable:** actor sin permisos.
- **Dónde mirar:** `workspace_access.py`.
- **Solución:** revisar rol/ACL.
- **Síntoma:** `NOT_FOUND` al leer.
- **Causa probable:** workspace inexistente o no visible.
- **Dónde mirar:** `get_workspace.py` y repositorio.
- **Solución:** validar IDs y policy.
- **Síntoma:** cambios de publish/archive no impactan.
- **Causa probable:** transición no persistida.
- **Dónde mirar:** `publish_workspace.py` / `archive_workspace.py`.
- **Solución:** revisar repositorio e inputs.
- **Síntoma:** share no surte efecto.
- **Causa probable:** ACL no persistida.
- **Dónde mirar:** `share_workspace.py` y `WorkspaceAclRepository`.
- **Solución:** revisar wiring en container.

## 🔎 Ver también
- `../README.md`
- `../../../interfaces/api/http/routers/workspaces.py`
- `../../../domain/workspace_policy.py`
- `../../../infrastructure/repositories/README.md`
