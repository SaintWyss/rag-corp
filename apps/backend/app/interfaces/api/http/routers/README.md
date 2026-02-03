# Routers HTTP

Como **ventanillas del mostrador**: cada router define un conjunto de endpoints por feature, arma el DTO de Application, aplica dependencias del borde y devuelve JSON/RFC7807/SSE.

## 🎯 Misión

`interfaces/api/http/routers/` contiene los **controllers finos** (thin controllers) de la API HTTP. Cada archivo representa un feature (workspaces, documents, query, admin) y su responsabilidad es estricta:

- recibir el request en FastAPI,
- validar/parsear usando schemas (en `../schemas/`),
- resolver dependencias del borde (actor, metadata, auth) desde `../dependencies.py`,
- construir el `*Input` del caso de uso,
- invocar el use case (Application),
- mapear el resultado a response (success o RFC7807; y SSE si aplica).

Recorridos rápidos por intención:

- **Quiero ver endpoints de documentos (upload/status/reprocess)** → `documents.py`
- **Quiero ver endpoints de workspaces (CRUD/share/publish/archive)** → `workspaces.py`
- **Quiero ver búsqueda/ask y streaming** → `query.py`
- **Quiero ver endpoints administrativos** → `admin.py`
- **Quiero ver schemas HTTP usados por estos routers** → `../schemas/README.md`
- **Quiero ver dependencias comunes (actor, uploads, headers)** → `../dependencies.py`
- **Quiero ver mapping a RFC7807** → `../error_mapping.py`
- **Quiero ver cómo se incluyen en el router raíz** → `../router.py`

### Qué SÍ hace

- Implementa endpoints HTTP por feature:
  - workspaces
  - documentos
  - query (search/ask/stream)
  - admin

- Aplica dependencias de borde:
  - construcción de `actor`
  - parsing de uploads (multipart)
  - metadata/correlation-id/request context

- Mapea errores tipados de use cases a:
  - RFC7807 Problem Details
  - status codes consistentes

- Expone streaming SSE cuando un endpoint lo define (normalmente en query).

### Qué NO hace (y por qué)

- No contiene lógica de negocio.
  - **Razón:** reglas/políticas pertenecen a Application/Domain.
  - **Impacto:** el router no decide permisos ni estados; pasa `actor` y delega a los use cases.

- No define schemas.
  - **Razón:** separar contratos (schemas) de controllers reduce acoplamiento y mejora la lectura.
  - **Impacto:** si cambia un contrato público, se toca `../schemas/` y el router solo ajusta mapping.

- No accede a DB ni a infraestructura.
  - **Razón:** infraestructura pertenece a `infrastructure/`.
  - **Impacto:** no hay SQL/psycopg/boto3/rq aquí; si aparece, es boundary roto.

## 🗺️ Mapa del territorio

| Recurso         | Tipo           | Responsabilidad (en humano)                                                      |
| :-------------- | :------------- | :------------------------------------------------------------------------------- |
| `__init__.py`   | Archivo Python | Exporta routers segmentados para imports estables en `../router.py`.             |
| `admin.py`      | Archivo Python | Endpoints administrativos (operaciones internas/privilegiadas).                  |
| `documents.py`  | Archivo Python | Endpoints de documentos (upload, status, reprocess, list/metadata).              |
| `query.py`      | Archivo Python | Endpoints de búsqueda/ask y streaming SSE (cuando aplica).                       |
| `workspaces.py` | Archivo Python | Endpoints de workspaces (crear, listar, get, update, publicar, archivar, share). |
| `README.md`     | Documento      | Portada + guía de navegación de routers por feature (este archivo).              |

## ⚙️ ¿Cómo funciona por dentro?

### Request → Router → Schema/DTO → Application → Response

- **Request:** FastAPI recibe request (path/query/body/multipart).
- **Router:** el módulo del feature declara el endpoint y dependencias.
- **Schema:** valida input/output con Pydantic (en `../schemas/`).
- **DTO:** el endpoint arma `*Input` del use case (Application).
- **Application:** ejecuta el caso de uso.
- **Response:**
  - éxito → JSON (response_model) con status code correcto.
  - error tipado → RFC7807 (Problem Details) vía `../error_mapping.py`.
  - streaming → SSE (query) con generator/async generator.

### Patrones que se repiten en estos routers

- **Thin controllers:** máximo “pegamento”; nada de decisiones de negocio.
- **Errores tipados:** no exponer excepciones internas; mapear a RFC7807.
- **Imports estables:** se importan use cases desde container o desde `application/` según patrón del repo.
- **Trazabilidad:** conservar `request_id`/correlation id cuando exista (por dependency).

### SSE (cuando aplica)

En endpoints de streaming (por ejemplo `POST /query/stream`):

- el router adapta el output del use case/LLM a eventos SSE.
- si ocurre un error durante el stream:
  - se emite un evento final (si el helper lo soporta) y se cierra.
  - no se reintenta durante la iteración (no hay idempotencia del output).

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Interfaces_ (HTTP adapter).

- **Recibe órdenes de:**
  - clientes HTTP.

- **Llama a:**
  - casos de uso en `app/application/usecases/` (vía container).
  - `../dependencies.py` para actor, uploads, request context.
  - `../error_mapping.py` para RFC7807.

- **Reglas de límites (imports/ownership):**
  - no SQL / no repos / no infra.
  - no reglas de negocio.
  - schemas viven en `../schemas/`.

## 👩‍💻 Guía de uso (Snippets)

### 1) Importar un subrouter desde el router raíz

```python
from app.interfaces.api.http.routers import query_router

# El router raíz lo incluye con include_router(query_router)
```

### 2) Router de feature (estructura mínima)

```python
from fastapi import APIRouter

router = APIRouter(prefix="/feature", tags=["feature"])

@router.get("/{item_id}")
def get_item(item_id: str):
    return {"id": item_id}
```

### 3) Endpoint típico: schema → DTO → use case

```python
from fastapi import APIRouter

from app.container import get_get_document_status_use_case
from app.application.usecases.ingestion.get_document_status import GetDocumentStatusInput

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/{document_id}/status")
def get_status(document_id: str):
    use_case = get_get_document_status_use_case()
    result = use_case.execute(GetDocumentStatusInput(document_id=document_id, actor=None))
    return result
```

### 4) Error mapping a RFC7807 (patrón)

```python
from fastapi import HTTPException

from app.interfaces.api.http.error_mapping import to_problem_details

def raise_problem(error, *, instance: str) -> None:
    problem = to_problem_details(error, instance=instance)
    raise HTTPException(status_code=problem.status, detail=problem.model_dump())
```

## 🧩 Cómo extender sin romper nada

1. **Crear un router nuevo por feature**

- Agregar `routers/<feature>.py`.
- Definir `router = APIRouter(prefix=..., tags=[...])`.

2. **Schemas**

- Agregar request/response models en `../schemas/<feature>.py`.
- Mantener nombres consistentes (`CreateXRequest`, `XResponse`).

3. **Incluirlo en el router raíz**

- Editar `../router.py` para `include_router`.
- Asegurar tags/prefix y responses RFC7807.

4. **Errores nuevos**

- Si el use case devuelve un error tipado nuevo:
  - agregar mapping en `../error_mapping.py`.

5. **Streaming**

- Si un endpoint es streaming:
  - usar un helper SSE (si existe) o un wrapper estándar.
  - manejar cancelación del cliente y exceptions.

6. **Tests**

- Integration/E2E:
  - endpoint visible en OpenAPI.
  - status codes correctos.
  - RFC7807 completo.
  - streaming: entrega eventos y cierra limpio.

## 🆘 Troubleshooting

1. **Endpoint no visible**

- Causa probable: el router no fue incluido en `../router.py`.
- Dónde mirar: `../router.py`.
- Solución: `include_router` del subrouter.

2. **403 inesperado**

- Causa probable: dependencia de permisos/actor retorna rol incorrecto o falta auth.
- Dónde mirar: `../dependencies.py` y el router afectado.
- Solución: validar headers/tokens y que el router use la dependency correcta.

3. **422 inesperado**

- Causa probable: schema no coincide con payload.
- Dónde mirar: `../schemas/`.
- Solución: alinear schema con contrato público.

4. **500 sin RFC7807**

- Causa probable: excepción no tipada o no mapeada.
- Dónde mirar: `../error_mapping.py` y handlers globales.
- Solución: traducir a error tipado y mapear.

5. **SSE no funciona / se corta**

- Causa probable: excepción en mitad del stream o generator mal adaptado.
- Dónde mirar: `query.py` y helpers SSE.
- Solución: try/except en generator, manejar cancelación y cerrar limpio.

## 🔎 Ver también

- `../README.md` (API HTTP: visión general)
- `../router.py` (composición del router raíz)
- `../schemas/README.md` (DTOs HTTP)
- `../dependencies.py` (actor, uploads, request context)
- `../error_mapping.py` (RFC7807)
- `../../../application/usecases/README.md` (casos de uso que consumen los endpoints)
