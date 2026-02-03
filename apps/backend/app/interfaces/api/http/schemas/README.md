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

- No contiene lógica de negocio. Razón: ** decisiones de negocio viven en Application/Domain. Impacto: ** un schema no decide permisos ni estados; solo valida formato y límites.

- No ejecuta queries ni llama servicios. Razón: ** IO pertenece a Infrastructure; orquestación a Application. Impacto: ** no hay repos/DB/LLM aquí; si aparece, es boundary roto.

- No debería depender de infraestructura ni de modelos de vendor. Razón: ** mantener schemas portables y predecibles. Impacto: ** evitar imports a `boto3`, `psycopg`, SDKs o clases internas de infraestructura.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :-------------- | :------------- | :-------------------------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Exporta schemas para imports estables desde routers (evita imports profundos). |
| `admin.py` | Archivo Python | DTOs de endpoints admin: requests/responses para operaciones privilegiadas. |
| `documents.py` | Archivo Python | DTOs de documentos: upload (multipart helpers en routers), list/get/status/reprocess, metadata y filtros. |
| `query.py` | Archivo Python | DTOs de query/ask/stream: query, top_k, filtros por workspace, opciones de streaming y respuestas. |
| `workspaces.py` | Archivo Python | DTOs de workspaces: create/update, publish/archive, share/ACL, list/get. |
| `README.md` | Documento | Portada + guía de navegación de schemas HTTP (este archivo). |

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
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.interfaces.api.http.schemas.query import AskReq

req = AskReq(query="¿Qué dice el contrato?")
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.interfaces.api.http.schemas.workspaces import WorkspaceResponse
```

```python
# Por qué: deja visible el flujo principal.
from app.crosscutting.config import get_settings
_settings = get_settings()
```

## 🧩 Cómo extender sin romper nada
- Agregá schemas nuevos en el archivo del feature correspondiente.
- Mantené constraints en línea con settings (`crosscutting.config`).
- Actualizá routers y response_model.
- Wiring: dependencias reales se obtienen desde `app/container.py` en routers.
- Tests: unit en `apps/backend/tests/unit/api/`.

## 🆘 Troubleshooting
- **Síntoma:** 422 inesperado.
- **Causa probable:** constraint demasiado estricto.
- **Dónde mirar:** schema del endpoint.
- **Solución:** ajustar límites en settings o schema.
- **Síntoma:** campo faltante en response.
- **Causa probable:** response_model no define el campo.
- **Dónde mirar:** schema de response.
- **Solución:** agregar el campo y mapear en router.
- **Síntoma:** serialización rara (UUID/datetime).
- **Causa probable:** tipo no serializable.
- **Dónde mirar:** schema.
- **Solución:** usar tipos estándar o configurar serialización.
- **Síntoma:** routers y schemas desalineados.
- **Causa probable:** cambios no propagados.
- **Dónde mirar:** router y schema correspondiente.
- **Solución:** alinear mapping.

## 🔎 Ver también
- `../routers/README.md`
- `../README.md`
- `../../../../crosscutting/config.py`
