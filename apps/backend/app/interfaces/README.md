# Interfaces (adaptadores entrantes)

Como la **recepción del backend**: recibe requests HTTP, los convierte a DTOs del sistema, llama a casos de uso y devuelve respuestas (incluyendo errores RFC7807).

## 🎯 Misión

`interfaces/` concentra los **adaptadores de entrada** del backend. En este proyecto, el entrypoint principal es HTTP (FastAPI), así que acá vive todo lo que convierte el mundo externo (requests, headers, body, auth) en invocaciones limpias a la capa _Application_.

Este README funciona como **portada + índice**: describe el boundary HTTP y te guía al punto exacto según lo que quieras tocar.

Recorridos rápidos por intención:

- **Quiero ver el router raíz y cómo se compone** → `./api/http/router.py` y `./api/http/README.md`
- **Quiero ver endpoints de workspaces/documents/query** → `./api/http/routers/` (subrouters por feature)
- **Quiero ver schemas (requests/responses) y validación** → `./api/http/schemas/`
- **Quiero ver cómo se mapean errores a RFC7807** → `./api/http/error_mapping.py` (y `app/crosscutting/error_responses.py`)
- **Quiero ver auth/headers/permisos en el borde** → `./api/http/dependencies/` (si existe en el repo)
- **Quiero ver SSE/streaming de respuestas** → router de query/chat en `./api/http/routers/` y helpers SSE (si existen)

### Qué SÍ hace

- Define el borde HTTP del sistema:
  - rutas, métodos, status codes.
  - validación de payloads.

- Traduce requests a DTOs de Application:
  - `schemas` → `*Input` de use cases.
  - parsing de IDs y normalización mínima.

- Traduce resultados/errores de Application a respuestas HTTP:
  - success JSON
  - streaming (SSE) cuando aplica
  - errores RFC7807 de forma consistente

- Centraliza composición de routers y schemas para que la API sea navegable.

### Qué NO hace (y por qué)

- No contiene reglas de negocio.
  - **Razón:** la lógica vive en Application/Domain.
  - **Impacto:** un router no decide “qué está permitido”; a lo sumo valida formato y delega a use cases.

- No accede directamente a DB.
  - **Razón:** DB pertenece a Infrastructure.
  - **Impacto:** si ves SQL/psycopg aquí, es un smell; la salida correcta es usar un caso de uso.

- No decide implementaciones (Postgres vs in-memory, Google vs fake).
  - **Razón:** eso lo decide el container.
  - **Impacto:** Interfaces solo pide use cases al container (o los recibe por DI).

## 🗺️ Mapa del territorio

| Recurso     | Tipo      | Responsabilidad (en humano)                                                  |
| :---------- | :-------- | :--------------------------------------------------------------------------- |
| `api/`      | Carpeta   | Adaptador HTTP (FastAPI): routers, schemas, dependencias y mapeo de errores. |
| `README.md` | Documento | Portada + guía de navegación de la capa de interfaces (este archivo).        |

## ⚙️ ¿Cómo funciona por dentro?

### Input → Proceso → Output (HTTP boundary)

- **Input:** request HTTP (path/query params, headers, body JSON o multipart).
- **Proceso:**
  1. Router valida y parsea el request usando Pydantic (schemas).
  2. Construye un DTO de Application (`*Input`) y un `actor` si hay auth.
  3. Llama al caso de uso correspondiente.
  4. Interpreta el resultado:
     - si es éxito → responde JSON con status code correcto.
     - si es error tipado → mapea a RFC7807 (status, title, detail, type, instance) y responde.
     - si es streaming → adapta el generator/async generator a SSE.

- **Output:**
  - JSON (success) / JSON RFC7807 (error) / SSE (stream).

### Flujo típico de un endpoint

Ejemplo mental (sin asumir nombres exactos):

1. `POST /workspaces` recibe `{name: "Legal"}`.
2. Schema valida: name no vacío.
3. Router construye `CreateWorkspaceInput(name, actor, owner_user_id)`.
4. Router llama `CreateWorkspaceUseCase.execute(input)`.
5. Si `WorkspaceError.FORBIDDEN` → `error_mapping` lo convierte a 403 RFC7807.
6. Si éxito → responde 201 con `WorkspaceResponse`.

### Conceptos mínimos (en contexto)

- **FastAPI**: framework ASGI (async) que organiza routers por `APIRouter`.
- **Pydantic**: valida y transforma payloads (tipado + errores 422).
- **RFC7807 (Problem Details)**: formato estándar para errores JSON (`type`, `title`, `status`, `detail`, `instance`).
- **SSE (Server-Sent Events)**: streaming unidireccional (texto/eventos) para entregar tokens/respuestas incrementales.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Interfaces_ (adapter entrante / boundary).

- **Recibe órdenes de:**
  - clientes HTTP (UI, curl, integraciones).

- **Llama a:**
  - Application (use cases) a través del container.
  - Crosscutting para:
    - config/settings
    - logging
    - RFC7807 (schemas/responses comunes)

- **Reglas de límites (imports/ownership):**
  - No importar repositorios Postgres, pools, ni servicios de infraestructura directamente.
  - No construir SQL ni usar `psycopg`.
  - No decidir políticas de negocio: si hay permisos, se pasa `actor` y se deja decidir al use case.

## 👩‍💻 Guía de uso (Snippets)

### 1) Composición: incluir router raíz en FastAPI

```python
from fastapi import FastAPI

from app.interfaces.api.http.router import router

app = FastAPI()
app.include_router(router)
```

### 2) Router nuevo por feature (patrón)

```python
from fastapi import APIRouter

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/{item_id}")
def get_example(item_id: str):
    return {"id": item_id}
```

### 3) Llamar a un use case desde un endpoint (sin negocio en HTTP)

```python
from fastapi import APIRouter

from app.container import get_create_workspace_use_case
from app.interfaces.api.http.schemas.workspaces import CreateWorkspaceRequest
from app.application.usecases.workspace.create_workspace import CreateWorkspaceInput

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.post("")
def create_workspace(payload: CreateWorkspaceRequest):
    use_case = get_create_workspace_use_case()
    result = use_case.execute(CreateWorkspaceInput(name=payload.name, actor=None, owner_user_id=payload.owner_user_id))
    return result
```

### 4) Error mapping a RFC7807 (idea de uso)

```python
from fastapi import HTTPException

from app.interfaces.api.http.error_mapping import to_problem_details

def raise_problem(error, *, instance: str) -> None:
    problem = to_problem_details(error, instance=instance)
    raise HTTPException(status_code=problem.status, detail=problem.model_dump())
```

## 🧩 Cómo extender sin romper nada

Checklist práctico para agregar endpoints/routers sin desordenar el borde:

1. **Crear schema**

- `api/http/schemas/<feature>.py`:
  - request models (input)
  - response models (output)
  - mantener nombres consistentes con use case (`CreateXRequest`, `XResponse`).

2. **Crear router**

- `api/http/routers/<feature>.py`:
  - endpoints finos
  - armar `*Input` del use case
  - llamar al use case
  - mapear resultado (success/error) sin lógica de negocio.

3. **Registrar router en el router raíz**

- `api/http/router.py`:
  - incluir el subrouter.
  - mantener tags/prefixes consistentes.

4. **Errores y RFC7807**

- Si aparece un nuevo error tipado en Application:
  - agregar mapping en `api/http/error_mapping.py`.
  - mantener la salida RFC7807 consistente con OpenAPI.

5. **Tests**

- Unit (schemas): validaciones, defaults, 422.
- Integration/E2E (routers): status codes correctos, problem details, happy path.

## 🆘 Troubleshooting

1. **422 inesperado**

- Causa probable: schema no coincide con payload real.
- Dónde mirar: `api/http/schemas/` (validators, required fields) y request real.
- Solución: alinear schema con contrato público; evitar defaults engañosos.

2. **500 sin detalle**

- Causa probable: error tipado sin mapping o excepción no capturada.
- Dónde mirar: `api/http/error_mapping.py` y logs del server.
- Solución: mapear el error a RFC7807 y asegurar `raise ... from exc` en capas inferiores.

3. **OpenAPI muestra errores inconsistentes**

- Causa probable: responses no centralizadas o faltan `responses={...}`.
- Dónde mirar: router raíz y `app/crosscutting/error_responses.py`.
- Solución: usar `OPENAPI_ERROR_RESPONSES` y mantener RFC7807 uniforme.

4. **SSE corta o se queda colgado**

- Causa probable: generator/async generator mal adaptado o excepción en mitad del stream.
- Dónde mirar: router de query/chat y helpers SSE.
- Solución: manejar cancelación y exceptions; no reintentar durante iteración del stream.

5. **CORS/headers/auth no aplican**

- Causa probable: dependencia no registrada o middleware mal configurado.
- Dónde mirar: `app/api/main.py` (middlewares) y `api/http/dependencies/`.
- Solución: registrar dependency global o por router, y testear con requests reales.

## 🔎 Ver también

- `./api/http/README.md` (detalle de la API HTTP: routers, schemas, streaming)
- `../application/usecases/README.md` (casos de uso: orquestación sin HTTP)
- `../crosscutting/error_responses.py` (RFC7807 y responses para OpenAPI)
- `../container.py` (wiring: instancias de use cases que consumen los routers)