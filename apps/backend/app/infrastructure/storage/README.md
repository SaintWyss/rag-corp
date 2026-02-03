# Storage (S3/MinIO)
Como un **depósito de archivos**: guarda y sirve binarios fuera de la DB, con URLs firmadas para descargar sin pasar por el backend.

## 🎯 Misión

Este módulo implementa el adaptador de almacenamiento de archivos sobre un backend **S3-compatible** (AWS S3 / MinIO). Expone una API estable (puerto `FileStoragePort`) para que los casos de uso suban/descarguen/borran archivos sin conocer `boto3` ni detalles del proveedor.

Recorridos rápidos por intención:

- **Quiero subir un archivo durante la ingesta** → `s3_file_storage.py` (`upload_file`) usado por `application/usecases/ingestion/upload_document.py`.
- **Quiero descargar el archivo para extraer texto** → `s3_file_storage.py` (`download_file`) usado por `application/usecases/ingestion/process_uploaded_document.py`.
- **Quiero borrar huérfanos ante fallas de DB** → `s3_file_storage.py` (`delete_file`) desde el rollback en `upload_document.py`.
- **Quiero entregar descarga directa al cliente** → `s3_file_storage.py` (`generate_presigned_url`).
- **Quiero entender errores y cómo se tipan** → `errors.py`.

### Qué SÍ hace

- Sube objetos al bucket (`put_object` o `upload_fileobj`).
- Descarga objetos a memoria (`get_object` + `Body.read()`).
- Elimina objetos (`delete_object`).
- Genera URLs presignadas para descarga (`generate_presigned_url`).
- Traduce fallas del SDK a errores tipados del subsistema (`StorageError` y derivados), sin filtrar excepciones de vendor.

### Qué NO hace (y por qué)

- No guarda metadata de documentos. Razón: ** la metadata vive en repositorios (DB) y se gobierna desde Application. Impacto: ** este adaptador no sabe `document_id`, `workspace_id`, estado ni tags; solo trabaja con `key`.

- No expone endpoints HTTP. Razón: ** el transporte pertenece a _Interfaces_. Impacto: ** si se necesita un endpoint para “descargar”, Interfaces genera una presigned URL o delega a un caso de uso que la genere.

- No implementa autorización/ACL. Razón: ** la autorización se decide en Domain/Application. Impacto: ** si se llama a storage con una key indebida, el adapter no puede “validar permisos”; solo ejecuta la operación.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :------------------- | :------------- | :------------------------------------------------------------------------------------------------------------------ |
| `__init__.py` | Archivo Python | Exporta el adapter y la jerarquía de errores para imports estables desde `app.container`. |
| `errors.py` | Archivo Python | Define `StorageError` y subclases (`Configuration/NotFound/Permission/Unavailable`) para manejo consistente arriba. |
| `s3_file_storage.py` | Archivo Python | Implementa `FileStoragePort` contra S3/MinIO: upload (bytes/stream), download (bytes), delete e URLs presignadas. |
| `README.md` | Documento | Portada + guía de navegación y contratos de este subsistema. |

## ⚙️ ¿Cómo funciona por dentro?

### 1) Configuración y construcción del cliente

- **Input:** `S3Config(bucket, access_key, secret_key, region?, endpoint_url?)`.
- **Proceso:**
  1. `S3FileStorageAdapter.__init__` valida fail-fast:
- `bucket` no vacío.
- `access_key/secret_key` no vacíos.

  2. Cliente inyectable para tests:
- si se pasa `client=...`, se usa tal cual.

  3. Lazy import:
- si no hay `client`, importa `boto3` dentro del constructor.
- si `boto3` no está instalado → `StorageConfigurationError("boto3 no está instalado.")`.

  4. Construye `boto3.client('s3', aws_access_key_id=..., aws_secret_access_key=..., region_name=..., endpoint_url=...)`.

**Por qué así:**

- Validación fail-fast evita correr en runtime con config incompleta.
- Lazy import reduce costo de arranque y evita dependencia dura en import-time.
- Cliente inyectable permite tests unitarios sin red y sin credenciales.

### 2) Upload (`upload_file`)

- **Input:** `key: str`, `content: bytes | BinaryIO`, `content_type: str | None`.
- **Proceso:**
  1. `_require_key(key)` (si está vacío → `StorageError("key de storage es requerido.")`).
  2. Normaliza `ContentType`:
- si `content_type` es `None`, usa `application/octet-stream`.

  3. Rama según tipo de `content`:
- **bytes/bytearray/memoryview** → `put_object(Bucket, Key, Body, ContentType)`.
- **stream (BinaryIO)** → `upload_fileobj(Fileobj, Bucket, Key, ExtraArgs={'ContentType': ...})`.

  4. Cualquier excepción se mapea con `_map_storage_error(exc, action='upload', key=...)`.

**Detalle importante:**

- La rama de stream existe para evitar OOM con archivos grandes. El puerto hoy permite pasar `BinaryIO`, aunque algunos casos de uso usen bytes.

### 3) Download (`download_file`)

- **Input:** `key: str`.
- **Proceso:**
  1. `get_object(Bucket, Key)`.
  2. `Body.read()` a memoria.
  3. cierre best-effort del body.
  4. mapeo de errores vía `_map_storage_error(action='download')`.

**Trade-off:**

- El port devuelve `bytes`; si en el futuro querés streaming real, eso implicaría extender el port (p. ej. `download_stream`).

### 4) Delete (`delete_file`)

- **Input:** `key: str`.
- **Proceso:** `delete_object(Bucket, Key)`.

**Diseño:**

- El delete en S3 suele ser idempotente: borrar una key inexistente no debería romper un flujo de cleanup.
- Si hay un error real (permiso/infra), se tipa y se eleva.

### 5) Presigned URL (`generate_presigned_url`)

- **Input:** `key: str`, `expires_in_seconds=3600`, `filename: str | None`.
- **Proceso:**
  1. `_require_key(key)`.
  2. sanitiza `expires_in_seconds` (si ≤ 0, usa 3600).
  3. arma `Params={'Bucket': ..., 'Key': ...}`.
  4. si `filename` está presente:
- agrega `ResponseContentDisposition='attachment; filename="..."'` (escapa comillas).

  5. llama `generate_presigned_url(ClientMethod='get_object', Params=params, ExpiresIn=...)`.
  6. errores mapeados con `_map_storage_error(action='presign')`.

### 6) Mapeo de errores (`_map_storage_error`)

Este adapter no filtra `botocore.exceptions`. Las traduce a un lenguaje de storage:

- **Unavailable (infra/red):**
- `EndpointConnectionError`, `ConnectTimeoutError`, `ReadTimeoutError` → `StorageUnavailableError("timeout/conexión")`.

- **ClientError (S3 estructurado):**
- `NoSuchKey` / `404` / `NotFound` → `StorageNotFoundError(key)`.
- `AccessDenied` / `InvalidAccessKeyId` / `SignatureDoesNotMatch` → `StoragePermissionError(...)`.
- `SlowDown` / `RequestTimeout` / `ServiceUnavailable` → `StorageUnavailableError(...)`.
- otros códigos → `StorageError(f"Fallo de storage ({action}). code={code}")`.

- **Fallback:** cualquier otra excepción → `StorageError(f"Fallo de storage ({action}).")`.

Observabilidad:

- En fallas de infra (timeouts), loguea `warning` con `action` y `key`.
- En `ClientError` desconocido o fallback genérico, loguea `exception` con contexto.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Infrastructure_ (adapter de IO / almacenamiento).

- **Recibe órdenes de:**
- Casos de uso en `application/` (ingestion, downloads, cleanup), vía el puerto `FileStoragePort`.

- **Llama a:**
- `boto3` / `botocore` (SDK S3) encapsulado dentro del adapter.

- **Reglas de límites (imports/ownership):**
- No importa FastAPI ni DTOs HTTP.
- No conoce repositorios, estados de documento ni ACL.
- No expone tipos de vendor (no se filtran `ClientError`/`EndpointConnectionError` hacia arriba).

Wiring en el container:

- `app/container.py:get_file_storage()` construye este adapter **solo si** están seteados:
- `Settings.s3_bucket`
- `Settings.s3_access_key`
- `Settings.s3_secret_key`
- opcional: `Settings.s3_region`, `Settings.s3_endpoint_url`

- Si falta algo requerido, devuelve `None` y los casos de uso deben tratarlo como `SERVICE_UNAVAILABLE`.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_file_storage

storage = get_file_storage()
if storage:
    storage.upload_file("documents/1/a.pdf", b"%PDF-...", "application/pdf")
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.storage import S3Config, S3FileStorageAdapter

storage = S3FileStorageAdapter(S3Config(bucket="rag-docs", access_key="...", secret_key="...", endpoint_url="http://localhost:9000"))
```

```python
# Por qué: deja visible el flujo principal.
url = storage.generate_presigned_url("documents/1/a.pdf", expires_in_seconds=600, filename="a.pdf")
```

## 🧩 Cómo extender sin romper nada
- Si agregás un backend nuevo, implementá `FileStoragePort` y errores equivalentes.
- Mantené `upload_file` soportando bytes y stream.
- Cableá el adapter en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/infrastructure/`, integration con MinIO si aplica.

## 🆘 Troubleshooting
- **Síntoma:** `StorageConfigurationError`.
- **Causa probable:** bucket o credenciales faltantes.
- **Dónde mirar:** settings `s3_*` y `container.py`.
- **Solución:** configurar credenciales.
- **Síntoma:** `StorageNotFoundError`.
- **Causa probable:** key inexistente.
- **Dónde mirar:** metadata del documento.
- **Solución:** revisar `storage_key`.
- **Síntoma:** `boto3` no instalado.
- **Causa probable:** dependencia ausente.
- **Dónde mirar:** `requirements.txt`.
- **Solución:** instalar dependencias del backend.
- **Síntoma:** presigned URL no descarga.
- **Causa probable:** policy del bucket o endpoint incorrecto.
- **Dónde mirar:** settings `s3_endpoint_url`.
- **Solución:** corregir endpoint/policy.

## 🔎 Ver también
- `../../domain/services.py`
- `../../application/usecases/ingestion/README.md`
- `../../container.py`
