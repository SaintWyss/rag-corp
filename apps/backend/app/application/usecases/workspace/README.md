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

  * **Razón:** el transporte es responsabilidad de *Interfaces*.
  * **Impacto:** los routers solo transforman request/response y delegan acá.
* No escribe SQL directo ni conoce la infraestructura.

  * **Razón:** mantener Application testeable y desacoplada.
  * **Impacto:** todo acceso a datos pasa por repositorios/puertos inyectados desde el container.

## 🗺️ Mapa del territorio

| Recurso                | Tipo           | Responsabilidad (en humano)                                                             |
| :--------------------- | :------------- | :-------------------------------------------------------------------------------------- |
| `__init__.py`          | Archivo Python | Exporta casos de uso y DTOs para imports estables desde otros módulos.                  |
| `archive_workspace.py` | Archivo Python | Marca un workspace como archivado y hace cumplir sus reglas de visibilidad.             |
| `create_workspace.py`  | Archivo Python | Crea workspaces aplicando validaciones y reglas de negocio del sistema.                 |
| `get_workspace.py`     | Archivo Python | Obtiene un workspace verificando acceso del actor (read).                               |
| `list_workspaces.py`   | Archivo Python | Lista workspaces visibles para el actor (según policy y ACL).                           |
| `publish_workspace.py` | Archivo Python | Cambia el estado de publicación/visibilidad del workspace.                              |
| `share_workspace.py`   | Archivo Python | Gestiona el compartir por ACL (agregar/quitar permisos).                                |
| `update_workspace.py`  | Archivo Python | Actualiza metadata del workspace respetando permisos (write).                           |
| `workspace_access.py`  | Archivo Python | Helpers de acceso read/write: centraliza reglas y evita duplicación entre casos de uso. |
| `workspace_results.py` | Archivo Python | DTOs de resultado y errores tipados para crear/listar/actualizar/compartir.             |
| `README.md`            | Documento      | Portada + guía de navegación del módulo.                                                |

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

  * *Interfaces* (routers HTTP) de workspaces y rutas administrativas.

* **Llama a:**

  * `WorkspaceRepository` (persistencia de workspace).
  * `WorkspaceAclRepository` (permisos y compartición).
  * Policy/entidades del dominio (ej. `WorkspaceActor`).

* **Reglas de límites (imports/ownership):**

  * Este módulo no conoce FastAPI ni DTOs HTTP.
  * No accede a DB directo ni importa implementaciones de infraestructura.
  * El cableado de dependencias vive en `app/container.py`.

## 👩‍💻 Guía de uso (Snippets)

### 1) Crear workspace (runtime vía container)

```python
from uuid import UUID

from app.application.usecases.workspace.create_workspace import CreateWorkspaceInput
from app.container import get_create_workspace_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_create_workspace_use_case()
result = use_case.execute(
    CreateWorkspaceInput(
        name="Legal",
        actor=WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.ADMIN),
        owner_user_id=UUID("11111111-1111-1111-1111-111111111111"),
    )
)

if result.error:
    raise RuntimeError(result.error.message)
print(result.workspace.id, result.workspace.name)
```

### 2) Listar workspaces visibles (para UI)

```python
from uuid import UUID

from app.application.usecases.workspace.list_workspaces import ListWorkspacesInput
from app.container import get_list_workspaces_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_list_workspaces_use_case()
result = use_case.execute(
    ListWorkspacesInput(
        actor=WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.EMPLOYEE)
    )
)

if result.error:
    raise RuntimeError(result.error.message)
print([w.name for w in result.workspaces])
```

### 3) Compartir workspace (ACL)

```python
from uuid import UUID

from app.application.usecases.workspace.share_workspace import ShareWorkspaceInput
from app.container import get_share_workspace_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_share_workspace_use_case()
result = use_case.execute(
    ShareWorkspaceInput(
        workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
        actor=WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.ADMIN),
        target_user_id=UUID("22222222-2222-2222-2222-222222222222"),
        grant_role=UserRole.EMPLOYEE,
    )
)

if result.error:
    raise RuntimeError(result.error.message)
print("shared")
```

### 4) Publicar / archivar (transición de estado)

```python
from uuid import UUID

from app.application.usecases.workspace.publish_workspace import PublishWorkspaceInput
from app.container import get_publish_workspace_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_publish_workspace_use_case()
result = use_case.execute(
    PublishWorkspaceInput(
        workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
        actor=WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.ADMIN),
        is_published=True,
    )
)

if result.error:
    raise RuntimeError(result.error.message)
print(result.workspace.is_published)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo caso de uso:** crea `foo_workspace.py` con su `FooWorkspaceInput/Result`.
2. **Reutilizá acceso:** llamá a helpers de `workspace_access` en vez de duplicar policy.
3. **Errores tipados:** agregá/extendé en `workspace_results.py` si aparece una nueva condición (con código y mensaje).
4. **Cableado:** exportá en `__init__.py` y agregá el getter correspondiente en `app/container.py`.
5. **Tests:**

   * unit: use case con repos fakes/mocks.
   * integration: repos + DB (si existe suite de integración en el repo).
   * e2e: router → use case → persistencia (si aplica).

## 🆘 Troubleshooting

* **`FORBIDDEN` al crear/actualizar** → actor sin permiso de escritura → revisar `create_workspace.py` / `update_workspace.py` y reglas en `workspace_access.py`.
* **`NOT_FOUND` al leer** → workspace inexistente o no visible para el actor → revisar `get_workspace.py` y la consulta de `WorkspaceRepository`.
* **No aparece en `list_workspaces`** → no cumple policy/ACL o está archivado/no publicado → revisar `list_workspaces.py` y `workspace_access.py`.
* **Share “no surte efecto”** → ACL no persistida o repo no inyectado correctamente → revisar `share_workspace.py` + cableado en `app/container.py`.
* **Cambios de publicación/archivado no impactan** → transición no guardada o se pisa con un update posterior → revisar `publish_workspace.py` / `archive_workspace.py` y el orden de llamadas al repositorio.

## 🔎 Ver también

* `../README.md` (índice de casos de uso)
* `../../../interfaces/api/http/routers/README.md` (entrada HTTP, mapeos y routers)
* `../../../domain/workspace_policy.py` (actor y reglas de acceso)
* `../../../infrastructure/repositories/README.md` (implementaciones de repositorios)
