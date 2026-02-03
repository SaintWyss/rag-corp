# Interfaces API

Como el **acceso principal** al backend: agrupa los adaptadores de API (hoy HTTP) y su estructura interna (routers, schemas, dependencias).

## 🎯 Misión

`interfaces/api/` es el punto de entrada de las **interfaces públicas** del backend. Hoy el canal activo es HTTP (FastAPI), pero este módulo existe para que la capa de Interfaces tenga un lugar claro donde crecer si mañana sumás otros transportes (por ejemplo: WebSockets, gRPC, CLI interna, etc.) sin mezclar todo en un único árbol.

Este README funciona como **portada + índice**: te dice qué hay adentro, cómo se conecta con Application y dónde tocar según tu intención.

Recorridos rápidos por intención:

- **Quiero ver el adaptador HTTP completo** → `./http/README.md`
- **Quiero endpoints (routers) por feature** → `./http/routers/`
- **Quiero request/response schemas (Pydantic)** → `./http/schemas/`
- **Quiero dependencias (auth/actor/context)** → `./http/dependencies/` (si existe)
- **Quiero ver mapeo de errores a RFC7807** → `./http/error_mapping.py`
- **Quiero ver composición del router raíz** → `./http/router.py`
- **Quiero ver dónde se monta en FastAPI** → `../../api/README.md` y `app/api/main.py`

### Qué SÍ hace

- Organiza el adaptador HTTP en un único lugar coherente.
- Expone las piezas públicas de la API:
  - routers
  - schemas
  - helpers/dependencies
  - error mapping

- Mantiene la interfaz del transporte separada del negocio:
  - la API construye DTOs de Application
  - delega la orquestación al use case

### Qué NO hace (y por qué)

- No define lógica de negocio.
  - **Razón:** el negocio vive en Application/Domain.
  - **Impacto:** si una regla cambia (permisos, políticas, estados), se cambia en use cases y la API solo adapta.

- No implementa infraestructura.
  - **Razón:** hablar con DB/Redis/S3/LLM es infraestructura.
  - **Impacto:** acá no hay SQL/psycopg/boto3/rq/google-genai; si aparece, es un boundary roto.

## 🗺️ Mapa del territorio

| Recurso     | Tipo      | Responsabilidad (en humano)                                                                            |
| :---------- | :-------- | :----------------------------------------------------------------------------------------------------- |
| `http/`     | Carpeta   | Adaptador HTTP (FastAPI): routers por feature, schemas Pydantic, dependencies y helpers (RFC7807/SSE). |
| `README.md` | Documento | Portada + guía de navegación de `interfaces/api` (este archivo).                                       |

## ⚙️ ¿Cómo funciona por dentro?

### Input → Proceso → Output

- **Input:** request HTTP (path/query, headers, body JSON/multipart).
- **Proceso:**
  1. Router (FastAPI) recibe el request.
  2. Schema (Pydantic) valida y tipa el payload.
  3. Se construye un `*Input` para el caso de uso (Application).
  4. Se invoca el use case.
  5. Se mapea el resultado a response:
     - success JSON
     - errores RFC7807
     - streaming SSE cuando aplica

- **Output:** respuesta HTTP (JSON / SSE) con status code consistente.

### Dónde vive cada cosa

- **Transporte / HTTP puro:** `http/routers/*`, `http/router.py`.
- **Contratos públicos (payloads):** `http/schemas/*`.
- **Orquestación / negocio:** `application/usecases/*` (no acá).
- **Errores estandarizados:** mapping en `http/error_mapping.py` + helpers crosscutting.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Interfaces_ (adapter entrante / API boundary).

- **Recibe órdenes de:**
  - clientes HTTP (UI, integraciones, curl).

- **Llama a:**
  - Application (use cases) por container.
  - Crosscutting para config/logging/RFC7807.

- **Reglas de límites (imports/ownership):**
  - no acceder a DB/Redis/S3/LLM directamente.
  - no decidir implementaciones (real/fake); eso es `app/container.py`.
  - no contener reglas de negocio; solo adaptar y mapear.

## 👩‍💻 Guía de uso (Snippets)

### 1) Importar router HTTP (composición)

```python
from app.interfaces.api.http.router import router

# router se monta en app/api/main.py (FastAPI app.include_router(router))
```

### 2) Patrón típico de wiring de routers

```python
from fastapi import APIRouter

from app.interfaces.api.http.routers import workspaces, documents

router = APIRouter()
router.include_router(workspaces.router)
router.include_router(documents.router)
```

### 3) Llamar a un use case desde HTTP (sin negocio en la API)

```python
from fastapi import APIRouter

from app.container import get_list_workspaces_use_case
from app.application.usecases.workspace.list_workspaces import ListWorkspacesInput

router = APIRouter(prefix="/workspaces")

@router.get("")
def list_workspaces():
    use_case = get_list_workspaces_use_case()
    result = use_case.execute(ListWorkspacesInput(actor=None))
    return result
```

## 🧩 Cómo extender sin romper nada

1. **Agregar un endpoint HTTP**

- Crear/editar un router en `http/routers/`.
- Definir/ajustar schemas en `http/schemas/`.
- Incluir el router en `http/router.py`.

2. **Agregar un transporte nuevo (futuro)**

- Crear un nuevo submódulo hermano de `http/` (ej. `ws/`, `grpc/`).
- Mantener el mismo contrato: adaptar transporte → llamar use cases → mapear errores.

3. **Errores / RFC7807**

- Si aparece un error tipado nuevo en Application:
  - agregar mapping en `http/error_mapping.py`.
  - asegurar que OpenAPI lo documente de forma consistente.

4. **Tests**

- Unit: schemas.
- Integration: routers + mapping RFC7807.

## 🆘 Troubleshooting

1. **Un endpoint no aparece**

- Causa probable: el router no fue incluido en `http/router.py`.
- Dónde mirar: `http/router.py`.
- Solución: incluir el subrouter y reiniciar.

2. **Errores salen sin RFC7807**

- Causa probable: mapping faltante o respuesta construida manualmente.
- Dónde mirar: `http/error_mapping.py` + routers.
- Solución: usar el mapping central y evitar `raise HTTPException(detail=str(e))` ad-hoc.

3. **Imports raros a infra/DB**

- Causa probable: boundary roto (la API está orquestando).
- Dónde mirar: router que contiene el import.
- Solución: mover la lógica a un use case y que la API solo adapte.

## 🔎 Ver también

- `./http/README.md` (HTTP: routers, schemas, dependencies, error mapping)
- `../../api/README.md` (composición de la app FastAPI y montaje de routers)
- `../../application/usecases/README.md` (use cases consumidos por la API)
- `../../crosscutting/error_responses.py` (RFC7807 y respuestas OpenAPI)
- `../../container.py` (wiring de use cases y dependencias)
