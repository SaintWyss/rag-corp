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
- **Quiero ver auth/headers/permisos en el borde** → `./api/http/dependencies.py`
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

- No contiene reglas de negocio. Razón: ** la lógica vive en Application/Domain. Impacto: ** un router no decide “qué está permitido”; a lo sumo valida formato y delega a use cases.

- No accede directamente a DB. Razón: ** DB pertenece a Infrastructure. Impacto: ** si ves SQL/psycopg aquí, es un smell; la salida correcta es usar un caso de uso.

- No decide implementaciones (Postgres vs in-memory, Google vs fake). Razón: ** eso lo decide el container. Impacto: ** Interfaces solo pide use cases al container (o los recibe por DI).

## 🗺️ Mapa del territorio

| Recurso     | Tipo      | Responsabilidad (en humano)                                                  |
| :---------- | :-------- | :--------------------------------------------------------------------------- |
| `api`       | Carpeta   | Adaptador HTTP (FastAPI): routers, schemas, dependencias y mapeo de errores. |
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

```python
# Por qué: muestra el contrato mínimo del módulo.
from app.interfaces.api.http.router import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.container import get_create_workspace_use_case
from app.application.usecases.workspace.create_workspace import CreateWorkspaceInput

use_case = get_create_workspace_use_case()
use_case.execute(CreateWorkspaceInput(name="Legal", actor=None, owner_user_id="..."))
```

## 🧩 Cómo extender sin romper nada

- Agregá schemas en `api/http/schemas/` y routers en `api/http/routers/`.
- Registrá el router en `api/http/router.py`.
- Cableá dependencias en `app/container.py`.
- Tests: unit de schemas en `apps/backend/tests/unit/api/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting

- **Síntoma:** 422 inesperado.
- **Causa probable:** schema no coincide con payload.
- **Dónde mirar:** `api/http/schemas/`.
- **Solución:** alinear schema con contrato público.
- **Síntoma:** 500 sin RFC7807.
- **Causa probable:** error sin mapping.
- **Dónde mirar:** `api/http/error_mapping.py`.
- **Solución:** mapear error tipado.
- **Síntoma:** ruta no aparece en OpenAPI.
- **Causa probable:** router no incluido.
- **Dónde mirar:** `api/http/router.py`.
- **Solución:** incluir router.
- **Síntoma:** SSE corta.
- **Causa probable:** excepción durante stream.
- **Dónde mirar:** router de query y `crosscutting/streaming.py`.
- **Solución:** manejar cancelación/errores.

## 🔎 Ver también

- `./api/README.md`
- `../application/README.md`
- `../crosscutting/README.md`
- `../container.py`
