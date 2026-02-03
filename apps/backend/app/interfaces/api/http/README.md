# API HTTP (FastAPI)

Como un **mostrador**: recibe pedidos HTTP, valida el payload, llama a casos de uso y entrega respuestas bien formateadas (incluyendo errores RFC7807 y streaming cuando aplica).

## 🎯 Misión

`interfaces/api/http/` implementa el adaptador HTTP del backend usando FastAPI. Es el **boundary** donde lo externo (requests, headers, multipart, SSE) se traduce a invocaciones limpias a _Application_ (use cases) y se traduce de vuelta a responses HTTP consistentes.

Este README es **portada + índice**: describe las piezas del adaptador y te lleva al archivo exacto según lo que querés ver/modificar.

Recorridos rápidos por intención:

- **Quiero ver el router raíz y cómo se compone la API** → `router.py`
- **Quiero ver endpoints por feature** → `routers/README.md` y `routers/`
- **Quiero ver contratos HTTP (Pydantic)** → `schemas/README.md` y `schemas/`
- **Quiero ver cómo se resuelve `actor`/request context** → `dependencies.py`
- **Quiero ver mapping de errores a RFC7807** → `error_mapping.py` (y `app/crosscutting/error_responses.py`)
- **Tengo imports viejos a `routes.py`** → `routes.py` (shim de compatibilidad)
- **Quiero ver dónde se monta el router en FastAPI** → `app/api/main.py` y `../../../api/README.md`

### Qué SÍ hace

- Define rutas HTTP por feature (workspaces, documents, query, admin).
- Valida y tipa requests/responses con Pydantic.
- Construye DTOs de Application (`*Input`) y llama a use cases.
- Traduce resultados y errores tipados a:
  - JSON de éxito
  - RFC7807 (Problem Details) para fallas
  - streaming (SSE) cuando aplica

- Centraliza responses de errores para OpenAPI (para que la documentación sea uniforme).

### Qué NO hace (y por qué)

- No contiene lógica de negocio ni acceso a DB.
  - **Razón:** negocio y orquestación pertenecen a Application/Domain; persistencia a Infrastructure.
  - **Impacto:** si un endpoint necesita “algo de DB”, eso se hace vía un caso de uso y repositorios; no desde el router.

- No ejecuta tareas de background.
  - **Razón:** procesamiento asíncrono va por worker/cola.
  - **Impacto:** el endpoint encola un job y devuelve un estado/ID; el worker hace el trabajo.

- No decide implementaciones (Google vs fake, Postgres vs in-memory).
  - **Razón:** esa decisión es del container.
  - **Impacto:** los routers piden use cases al container; no instancian infraestructura.

## 🗺️ Mapa del territorio

| Recurso            | Tipo           | Responsabilidad (en humano)                                                                                                   |
| :----------------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| `dependencies.py`  | Archivo Python | Helpers comunes de borde: construir `actor`, request metadata, parsing de uploads/headers y utilidades repetidas por routers. |
| `error_mapping.py` | Archivo Python | Traduce errores tipados de use cases (p. ej. `DocumentError`, `WorkspaceError`) a RFC7807 (status/title/detail/type).         |
| `router.py`        | Archivo Python | Router raíz: compone sub-routers por feature y centraliza `responses` (RFC7807) para OpenAPI.                                 |
| `routes.py`        | Archivo Python | Shim de compatibilidad: re-exporta el router para imports antiguos sin romper rutas.                                          |
| `routers/`         | Carpeta        | Endpoints por feature: cada módulo arma DTOs, llama use cases y mapea resultados.                                             |
| `schemas/`         | Carpeta        | Contratos HTTP (Pydantic): request/response models, enums y validators de borde.                                              |
| `README.md`        | Documento      | Portada + guía del adaptador HTTP (este archivo).                                                                             |

## ⚙️ ¿Cómo funciona por dentro?

### Request → Router → Schema/DTO → Application → Response

- **Request:** FastAPI recibe la llamada (path, query, headers, body JSON o multipart).
- **Router:** `router.py` enruta al sub-router correcto (por prefijo/tags).
- **Schema:** Pydantic valida el payload y produce un objeto tipado.
- **DTO:** el endpoint construye un `*Input` de Application (y resuelve `actor`).
- **Application:** se ejecuta el caso de uso.
- **Response:**
  - éxito → JSON tipado (o raw JSON simple) con el status code correcto.
  - error tipado → mapping a RFC7807 (Problem Details).
  - streaming → adaptación a SSE (si ese endpoint lo ofrece).

### Dónde vive cada responsabilidad

- **Composición y OpenAPI:** `router.py`.
- **Validación pública:** `schemas/`.
- **Adaptación request → use case:** `routers/` + `dependencies.py`.
- **Errores:** `error_mapping.py` + `app/crosscutting/error_responses.py`.

### Conceptos mínimos (en contexto)

- **FastAPI / ASGI:** servidor async; los routers se montan con `include_router`.
- **Pydantic:** valida y transforma inputs; errores de validación devuelven 422.
- **RFC7807:** formato estándar para errores JSON (`type`, `title`, `status`, `detail`, `instance`).
- **SSE:** streaming unidireccional; útil para respuestas incrementales del LLM.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Interfaces_ (HTTP adapter).

- **Recibe órdenes de:**
  - clientes HTTP (UI, integraciones, curl).

- **Llama a:**
  - Application (use cases), típicamente obtenidos desde `app/container.py`.
  - Crosscutting:
    - settings/config
    - logging
    - RFC7807 responses para OpenAPI

- **Reglas de límites (imports/ownership):**
  - No importar `psycopg`, repositorios Postgres ni `db/pool` directamente.
  - No importar `boto3`, `rq`, ni SDKs de IA.
  - No tener lógica de negocio (políticas/estados). Validar formato sí; decidir reglas no.

## 👩‍💻 Guía de uso (Snippets)

### 1) Construir el router raíz (composición)

```python
from app.interfaces.api.http.router import build_router

api_router = build_router()
```

### 2) Montar el router en FastAPI

```python
from fastapi import FastAPI

from app.interfaces.api.http.router import build_router

app = FastAPI()
app.include_router(build_router())
```

### 3) Endpoint típico: schema → DTO → use case → mapping

```python
from fastapi import APIRouter

from app.container import get_get_workspace_use_case
from app.application.usecases.workspace.get_workspace import GetWorkspaceInput
from app.interfaces.api.http.schemas.workspaces import GetWorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.get("/{workspace_id}", response_model=GetWorkspaceResponse)
def get_workspace(workspace_id: str):
    use_case = get_get_workspace_use_case()
    result = use_case.execute(GetWorkspaceInput(workspace_id=workspace_id, actor=None))
    return result
```

### 4) Mapping de error tipado a RFC7807 (idea de uso)

```python
from fastapi import HTTPException

from app.interfaces.api.http.error_mapping import to_problem_details

def raise_problem(error, *, instance: str) -> None:
    problem = to_problem_details(error, instance=instance)
    raise HTTPException(status_code=problem.status, detail=problem.model_dump())
```

## 🧩 Cómo extender sin romper nada

1. **Agregar un router por feature**

- Crear `routers/<feature>.py` con:
  - `APIRouter(prefix=..., tags=[...])`
  - endpoints finos (sin orquestación compleja)
  - construcción de `*Input` para el caso de uso

2. **Agregar/ajustar schemas**

- `schemas/<feature>.py`:
  - request models
  - response models
  - validators de borde (formato, bounds, enums)

3. **Incluir el router nuevo en `router.py`**

- `build_router()` debe `include_router()` del sub-router.
- Mantener responses RFC7807 en el router raíz para OpenAPI.

4. **Agregar mapping de errores nuevos**

- Si aparece un error tipado nuevo en Application:
  - mapearlo en `error_mapping.py`.
  - asegurar `type/title/status/detail` consistentes.

5. **No romper compatibilidad**

- Si hay imports externos que usan `routes.py`, mantener el shim.
- Si se renombra un router, dejar un alias o redirect interno, no borrar de una.

6. **Tests**

- Unit: schemas (422, defaults, validadores).
- Integration/E2E:
  - status codes correctos
  - RFC7807 completo
  - endpoints críticos (upload, query, workspaces)

## 🆘 Troubleshooting

1. **`422 Unprocessable Entity` inesperado**

- Causa probable: schema no coincide con el payload real.
- Dónde mirar: `schemas/` (required fields, tipos, validators) y request real.
- Solución: alinear contrato público; evitar validaciones que rompan compatibilidad sin versionar.

2. **`500` sin RFC7807**

- Causa probable: excepción no tipada o sin mapping.
- Dónde mirar: `error_mapping.py` y handlers globales en API (si existen).
- Solución: traducir a error tipado en Application/Infrastructure y mapear a RFC7807.

3. **Rutas no aparecen en OpenAPI**

- Causa probable: sub-router no incluido en `router.py`.
- Dónde mirar: `router.py`.
- Solución: `include_router` + tags/prefix correctos.

4. **Endpoint devuelve JSON “crudo” sin response_model**

- Causa probable: falta `response_model` o el router retorna tipos no serializables.
- Dónde mirar: router del endpoint.
- Solución: usar schemas de response y retornar objetos serializables.

5. **Upload falla (multipart / tamaño)**

- Causa probable: parsing en `dependencies.py` o límites del servidor.
- Dónde mirar: `dependencies.py` + configuración del server.
- Solución: validar MIME/tamaño y asegurar que el pipeline use streaming cuando sea posible.

6. **SSE corta o se cuelga**

- Causa probable: excepción durante el stream o falta de manejo de cancelación.
- Dónde mirar: router de query/chat en `routers/` y helpers SSE.
- Solución: manejar cancelación, try/except en generator y devolver eventos de cierre.

## 🔎 Ver también

- `./routers/README.md` (endpoints por feature)
- `./schemas/README.md` (DTOs HTTP y validación)
- `../../../api/README.md` (composición de la app y montaje del router)
- `app/crosscutting/error_responses.py` (RFC7807 y OpenAPI responses)
- `app/container.py` (wiring de use cases consumidos por routers)
