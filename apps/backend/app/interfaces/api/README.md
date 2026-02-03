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

- No define lógica de negocio. Razón: ** el negocio vive en Application/Domain. Impacto: ** si una regla cambia (permisos, políticas, estados), se cambia en use cases y la API solo adapta.

- No implementa infraestructura. Razón: ** hablar con DB/Redis/S3/LLM es infraestructura. Impacto: ** acá no hay SQL/psycopg/boto3/rq/google-genai; si aparece, es un boundary roto.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :---------- | :-------- | :----------------------------------------------------------------------------------------------------- |
| `http` | Carpeta | Adaptador HTTP (FastAPI): routers por feature, schemas Pydantic, dependencies y helpers (RFC7807/SSE). |
| `README.md` | Documento | Portada + guía de navegación de `interfaces/api` (este archivo). |

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
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.interfaces.api.http.router import router
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.interfaces.api.http.schemas.workspaces import CreateWorkspaceRequest
```

## 🧩 Cómo extender sin romper nada
- Si agregás transporte nuevo, creá un submódulo hermano de `http/`.
- Mantener contrato: adaptar transporte → llamar use cases → mapear errores.
- Cableá dependencias en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/api/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** endpoint no aparece.
- **Causa probable:** router no incluido.
- **Dónde mirar:** `http/router.py`.
- **Solución:** incluir router.
- **Síntoma:** errores sin RFC7807.
- **Causa probable:** mapping faltante.
- **Dónde mirar:** `http/error_mapping.py`.
- **Solución:** mapear error tipado.
- **Síntoma:** imports a infra.
- **Causa probable:** boundary roto.
- **Dónde mirar:** router afectado.
- **Solución:** mover lógica a use case.
- **Síntoma:** 422 inesperado.
- **Causa probable:** schema desalineado.
- **Dónde mirar:** `http/schemas/`.
- **Solución:** ajustar schema.

## 🔎 Ver también
- `./http/README.md`
- `../../api/README.md`
- `../../application/usecases/README.md`
- `../../container.py`
