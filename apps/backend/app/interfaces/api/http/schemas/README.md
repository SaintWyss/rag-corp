# Schemas HTTP

Como un **formulario oficial**: define exactamente qué puede entrar y salir por la API, valida forma y límites, y garantiza contratos estables entre clientes y use cases.

## 🎯 Misión

`interfaces/api/http/schemas/` contiene los **DTOs públicos** del adaptador HTTP: modelos de request/response que FastAPI valida con Pydantic. Esta capa es el contrato que consumen clientes (UI, integraciones, curl) y el contrato interno que consumen los routers para construir inputs de Application.

Los schemas cumplen dos objetivos simultáneos:

- **Contrato público estable:** nombres, tipos y estructura de payloads.
- **Guardrails del borde:** validaciones y límites para evitar inputs inválidos, cargas excesivas y errores difíciles de trazar.

Recorridos rápidos por intención:

- **Quiero ver DTOs de documentos (upload/list/get/status)** → `documents.py`
- **Quiero ver DTOs de workspaces (create/update/share/publish/archive)** → `workspaces.py`
- **Quiero ver DTOs de query/ask/stream** → `query.py`
- **Quiero ver DTOs administrativos** → `admin.py`
- **Quiero ver cómo estos schemas se usan en endpoints** → `../routers/README.md` y `../routers/`
- **Quiero entender límites configurables (max_query_chars, max_top_k, etc.)** → `app/crosscutting/config.py` y `app/crosscutting/README.md`

### Qué SÍ hace

- Modela payloads de entrada/salida para features expuestas por HTTP:
  - workspaces
  - documents
  - query
  - admin

- Aplica validaciones con Pydantic:
  - tipos (UUID, str, int, bool)
  - required/optional
  - constraints (min/max, regex, longitudes)
  - normalizaciones mínimas (strip)

- Aplica límites defensivos configurables:
  - largo máximo de query
  - top_k máximo
  - límites de streaming/buffers (cuando corresponda)

- Mantiene contratos consistentes para routers:
  - responses serializables
  - nombres estables
  - versionado explícito cuando sea necesario (ideal: introducir `v1/` si alguna vez cambia públicamente)

### Qué NO hace (y por qué)

- No contiene lógica de negocio.
  - **Razón:** decisiones de negocio viven en Application/Domain.
  - **Impacto:** un schema no decide permisos ni estados; solo valida formato y límites.

- No ejecuta queries ni llama servicios.
  - **Razón:** IO pertenece a Infrastructure; orquestación a Application.
  - **Impacto:** no hay repos/DB/LLM aquí; si aparece, es boundary roto.

- No debería depender de infraestructura ni de modelos de vendor.
  - **Razón:** mantener schemas portables y predecibles.
  - **Impacto:** evitar imports a `boto3`, `psycopg`, SDKs o clases internas de infraestructura.

## 🗺️ Mapa del territorio

| Recurso         | Tipo           | Responsabilidad (en humano)                                                                               |
| :-------------- | :------------- | :-------------------------------------------------------------------------------------------------------- |
| `__init__.py`   | Archivo Python | Exporta schemas para imports estables desde routers (evita imports profundos).                            |
| `admin.py`      | Archivo Python | DTOs de endpoints admin: requests/responses para operaciones privilegiadas.                               |
| `documents.py`  | Archivo Python | DTOs de documentos: upload (multipart helpers en routers), list/get/status/reprocess, metadata y filtros. |
| `query.py`      | Archivo Python | DTOs de query/ask/stream: query, top_k, filtros por workspace, opciones de streaming y respuestas.        |
| `workspaces.py` | Archivo Python | DTOs de workspaces: create/update, publish/archive, share/ACL, list/get.                                  |
| `README.md`     | Documento      | Portada + guía de navegación de schemas HTTP (este archivo).                                              |

## ⚙️ ¿Cómo funciona por dentro?

### Request → Schema → Application → Response

- **Request:** FastAPI recibe JSON (o multipart/form-data para uploads).
- **Schema:** Pydantic:
  1. parsea tipos (UUIDs, ints, enums).
  2. valida constraints (min/max, longitudes, regex).
  3. aplica normalizaciones mínimas (strip) si existen.

- **Application:** el router crea `*Input` de use case usando los valores ya validados.
- **Response:** el router devuelve un objeto:
  - Pydantic lo serializa a JSON.
  - si hay errores, se devuelven por RFC7807 (eso lo maneja `error_mapping.py`, no los schemas).

### Validaciones típicas (patrones)

- **Strings**
  - `min_length=1` para campos obligatorios (ej. `name`, `title`).
  - `max_length=Settings.max_*` para evitar payloads gigantes.
  - `strip_whitespace=True` para evitar inputs “vacíos” con espacios.

- **Enteros**
  - `ge=1` y `le=Settings.max_top_k` para `top_k`.
  - `ge=0` para offsets/paginación.

- **UUIDs**
  - parseo directo a `UUID` para evitar strings inválidos.

- **Enums**
  - en requests públicos, usar enums explícitos para evitar strings libres.

### Límites configurables

Los schemas no “inventan” límites: se apoyan en settings del sistema para coherencia global.
Ejemplos típicos:

- `max_query_chars`
- `max_top_k`
- `max_title_chars`
- `max_upload_bytes` (aunque el enforcement duro suele estar en routers/middleware)

> Regla práctica: si el límite afecta a clientes, debe vivir en config y reflejarse en schemas.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Interfaces_ (DTOs HTTP / contratos públicos).

- **Recibe órdenes de:**
  - routers HTTP en `../routers/`.

- **Llama a:**
  - settings/config para límites (por ejemplo `get_settings()`), sin IO.

- **Reglas de límites (imports/ownership):**
  - schemas no dependen de infraestructura.
  - schemas no importan repositorios ni servicios.
  - schemas no crean `*Input` de Application (eso es responsabilidad del router).

## 👩‍💻 Guía de uso (Snippets)

### 1) Construir un request model (uso directo)

```python
from app.interfaces.api.http.schemas.query import AskReq

req = AskReq(query="¿Qué dice el contrato?")
print(req.query)
```

### 2) Validación automática (raise en inválidos)

```python
from pydantic import ValidationError

from app.interfaces.api.http.schemas.query import AskReq

try:
    AskReq(query="")  # inválido si min_length=1
except ValidationError as e:
    print(e)
```

### 3) Response model (serializable)

```python
from uuid import uuid4

from app.interfaces.api.http.schemas.workspaces import WorkspaceResponse

resp = WorkspaceResponse(
    id=uuid4(),
    name="Legal",
    is_published=False,
)
print(resp.model_dump())
```

### 4) Usar límites desde config (patrón)

```python
from pydantic import BaseModel, Field

from app.crosscutting.config import get_settings

_settings = get_settings()

class AskReq(BaseModel):
    query: str = Field(min_length=1, max_length=_settings.max_query_chars)
```

## 🧩 Cómo extender sin romper nada

Checklist para agregar/ajustar schemas sin romper clientes:

1. **Agregar schema por endpoint**

- Crear/editar `schemas/<feature>.py`.
- Definir request/response models con nombres explícitos.

2. **Mantener contratos estables**

- No renombrar campos públicos sin un plan de compatibilidad.
- Si necesitás cambiar forma de payload, introducir versionado (ej. `v1/`, o mantener alias de campos).

3. **Validaciones en el borde, no negocio**

- Validar formato (UUID, longitudes, enums).
- No validar “permisos”, “estado válido” o “existe en DB” (eso es Application).

4. **Límites desde settings**

- Cualquier max/min que impacte al usuario debe estar en config.
- Evitar números mágicos dispersos.

5. **Documentación de campos**

- Usar `Field(description=...)` en campos públicos importantes.
- Mantener consistencia de nombres (snake_case vs camelCase según estándar del proyecto).

6. **Tests**

- Unit: validar que constraints funcionan (422 en HTTP).
- Compat: si cambiaste un schema, agregar test que cubra el payload anterior si se mantiene.

## 🆘 Troubleshooting

1. **`422` en requests que “parecen válidos”**

- Causa probable: constraints más restrictivos de lo esperado (max_length, enum, required).
- Dónde mirar: schema específico en `schemas/<feature>.py`.
- Solución: ajustar límites en config o relajar constraint (con criterio).

2. **Límites muy bajos / demasiado altos**

- Causa probable: settings mal configurados.
- Dónde mirar: `app/crosscutting/config.py`.
- Solución: actualizar settings (env) y asegurar que los schemas usen esos valores.

3. **Campo “faltante” en response**

- Causa probable: el response_model no lo define o está marcado optional con default.
- Dónde mirar: schema de response correspondiente.
- Solución: definir el campo y revisar que el router lo complete.

4. **Serialización rara (UUID/datetime)**

- Causa probable: configuración de Pydantic o tipos no serializables.
- Dónde mirar: el modelo y su config (`model_config` / `json_encoders`).
- Solución: usar tipos estándar (UUID/datetime) y configurar serialización si hace falta.

5. **Inconsistencia entre routers y schemas**

- Causa probable: el router construye un payload distinto al schema.
- Dónde mirar: router del endpoint y el schema asociado.
- Solución: alinear mapping; preferir `response_model` y `model_dump()` controlado.

## 🔎 Ver también

- `../routers/README.md` (endpoints que consumen estos schemas)
- `../README.md` (visión general del adaptador HTTP)
- `../../../../crosscutting/README.md` (settings, límites y convenciones)
- `../../../../crosscutting/config.py` (valores de `max_*` y flags)
- `../error_mapping.py` (RFC7807; los schemas no mapean errores)
