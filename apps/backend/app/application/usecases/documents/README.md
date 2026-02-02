# Use Cases: Documents

Analogía breve: este paquete es el **mostrador de documentos** del sistema. Acá se decide quién puede ver qué, cómo se lista, cómo se obtiene el detalle, cómo se descarga el archivo real y cómo se actualiza metadata sin romper invariantes.

## 🎯 Misión

Este directorio implementa los casos de uso relacionados a **Documentos** dentro de un workspace: listar, obtener, descargar, actualizar metadata y eliminar (soft delete). Además concentra el contrato de **errores/resultados tipados** compartidos (`DocumentError`, `DocumentErrorCode`) para que:

* HTTP pueda mapear consistentemente a RFC7807.
* El resto de la aplicación (chat/ingestion) reutilice códigos de error estables.
* Los tests aserten por `error.code` sin depender de strings.

Ruta rápida (si estás apurado):

* **Errores y resultados compartidos:** `document_results.py`
* **Listar documentos:** `list_documents.py`
* **Ver un documento (metadata):** `get_document.py`
* **Descargar archivo (bytes/stream):** `download_document.py`
* **Actualizar metadata/tags:** `update_document_metadata.py`
* **Eliminar (soft delete):** `delete_document.py`

**Qué SÍ hace**

* Aplica policy de acceso al workspace (read/write) antes de tocar repos.
* Normaliza y valida cambios de metadata (tags, título, flags) con reglas defensivas.
* Mantiene la semántica de **soft delete**: se archiva/inactiva el documento sin borrarlo físicamente por defecto.
* Traduce errores operativos y de negocio a `DocumentError` con códigos estables.

**Qué NO hace (y por qué)**

* No implementa DB o storage concretos.

  * **Por qué:** se trabaja contra puertos (`DocumentRepository`, `FileStoragePort`, etc.). Implementaciones viven en `infrastructure/`.
* No expone endpoints HTTP ni schemas Pydantic.

  * **Por qué:** `interfaces/` convierte request → Input; estos use cases son agnósticos al transporte.
* No “reconstruye” chunks o embeddings.

  * **Por qué:** el pipeline de ingesta vive en `usecases/ingestion/` y la búsqueda en `usecases/chat/`.

---

## 🗺️ Mapa del territorio

| Recurso                       | Tipo         | Responsabilidad (en humano)                                                                                          |
| :---------------------------- | :----------- | :------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`                 | 🐍 Archivo   | Exporta Inputs/UseCases/Results de documentos y el contrato `DocumentError`.                                         |
| `document_results.py`         | 🐍 Archivo   | Contratos compartidos: `DocumentErrorCode`, `DocumentError`, y resultados tipados usados también por chat/ingestion. |
| `list_documents.py`           | 🐍 Archivo   | Lista documentos de un workspace con paginación y filtros defensivos (limit/offset, sort).                           |
| `get_document.py`             | 🐍 Archivo   | Devuelve metadata de un documento por ID, validando que pertenezca al workspace y sea accesible.                     |
| `download_document.py`        | 🐍 Archivo   | Resuelve `storage_key`/path del documento y delega al port de storage para obtener el contenido.                     |
| `update_document_metadata.py` | 🐍 Archivo   | Actualiza campos permitidos de metadata y normaliza tags/valores; mantiene invariantes.                              |
| `delete_document.py`          | 🐍 Archivo   | Aplica **soft delete** (marca estado/archivado) y opcionalmente dispara cleanup según policy.                        |
| `README.md`                   | 📄 Documento | Portada + guía técnica del bounded context Documents (este archivo).                                                 |

---

## ⚙️ ¿Cómo funciona por dentro?

### 1) El contrato común: Inputs/Results + `DocumentError`

Los use cases de documentos tienden a devolver resultados con `error` tipado:

* `DocumentErrorCode` (códigos estables)
* `DocumentError` (code + message + resource + details)

La idea no es “hacer burocracia”, sino garantizar tres cosas:

1. **Mismo error → mismo comportamiento** en HTTP y Worker.
2. **No filtrar secretos** (URLs firmadas, credenciales, paths internos).
3. **Debug rápido**: `resource` te dice “qué” falló (document_id, workspace_id, storage_key).

### 2) Policy de acceso a Workspace (antes que repos)

Todos los casos de uso que leen/escriben documentos hacen el mismo paso primero:

* Resolver el workspace y verificar acceso:

  * lectura (`resolve_workspace_for_read`) para listar/obtener/descargar
  * escritura (`resolve_workspace_for_write`) para update/delete

Esto evita un error común: “si el documento existe pero no tenés acceso”, el sistema no revela existencia fuera del scope.

### 3) Listado (ListDocuments)

`list_documents.py` se enfoca en un listado seguro y predecible:

* Paginación defensiva:

  * `limit` con máximo fijo (anti‑OOM)
  * `offset` o cursor (según contrato)
* Filtros permitidos:

  * por estado (activos/archivados)
  * por query de título/tags
  * por fecha (si aplica)
* Orden:

  * campo permitido (no “order_by libre”)

Salida típica:

* lista de `DocumentSummary` / `DocumentView`
* `total` (si el repo lo soporta)
* metadata de paginación

### 4) Obtener (GetDocument)

`get_document.py`:

* verifica acceso al workspace
* carga documento por `document_id`
* valida pertenencia (workspace_id)
* valida estado (no archivado si el contrato lo requiere)

Salida:

* entidad/DTO de documento con metadata (sin bytes)

### 5) Descargar (DownloadDocument)

`download_document.py` separa dos preocupaciones:

1. autorización y pertenencia al workspace
2. fetch de bytes desde storage

Importante:

* El use case no “abre archivos” directamente.
* Llama a `FileStoragePort` con una llave estable (`storage_key` o path) y recibe bytes/stream.

Esto permite cambiar:

* MinIO ↔ S3 ↔ filesystem
  sin tocar el caso de uso.

### 6) Update metadata (UpdateDocumentMetadata)

`update_document_metadata.py` aplica validaciones que no dependen del transporte:

* normaliza tags:

  * trim
  * lowercase/slug si corresponde
  * deduplicación estable
  * límites por cantidad/longitud
* controla campos editables:

  * título
  * tags
  * flags
* actualiza `updated_at` y `updated_by` si el repositorio lo soporta

### 7) Soft delete (DeleteDocument)

`delete_document.py` implementa eliminación lógica:

* cambia estado (archivado / eliminado lógico)
* conserva `document_id` para trazabilidad
* puede disparar un cleanup (opcional) que típicamente vive como:

  * job async
  * policy de retención

Por qué soft delete:

* evita pérdidas accidentales
* mantiene integridad referencial
* permite auditoría y recuperación

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Application (Use Cases / Documents).

* **Recibe órdenes de:**

  * Interfaces HTTP (`routers/documents.py`) para CRUD.
  * Worker (por ejemplo, limpieza/retención si se encola).

* **Llama a (puertos típicos):**

  * `DocumentRepository` (leer/listar/actualizar/archivar)
  * `WorkspaceRepository` + `WorkspaceAclRepository` (enforce acceso)
  * `FileStoragePort` (download; y eventualmente delete físico)

* **Límites:**

  * sin SQL/SDKs directos
  * sin FastAPI
  * errores tipados para mapeo RFC7807

---

## 👩‍💻 Guía de uso (Snippets)

> Estos ejemplos muestran el estilo de invocación desde “código interno” o tests. En runtime, HTTP construye Inputs desde DTOs.

### A) Obtener documento (metadata)

```python
from uuid import uuid4

from app.container import get_get_document_use_case

use_case = get_get_document_use_case()
result = use_case.execute(
    document_id=uuid4(),
    workspace_id=uuid4(),
    actor=None,
)

if result.error:
    raise RuntimeError(f"{result.error.code}: {result.error.message}")

print(result.document)
```

### B) Listar documentos (paginación defensiva)

```python
from uuid import uuid4

from app.container import get_list_documents_use_case

use_case = get_list_documents_use_case()
result = use_case.execute(
    workspace_id=uuid4(),
    actor=None,
    limit=20,
    offset=0,
)

if result.error:
    raise RuntimeError(result.error)

print(result.total, len(result.items))
```

### C) Descargar contenido

```python
from uuid import uuid4

from app.container import get_download_document_use_case

use_case = get_download_document_use_case()
result = use_case.execute(
    document_id=uuid4(),
    workspace_id=uuid4(),
    actor=None,
)

if result.error:
    raise RuntimeError(result.error)

# bytes/stream según el contrato del Result
payload = result.payload
print(type(payload), getattr(result, "content_type", None))
```

---

## 🧩 Cómo extender sin romper nada

1. **Reutilizá `document_results.py`**

   * si agregás una operación nueva, devolvé `DocumentError` con códigos existentes.
   * si necesitás un nuevo código, agregalo con cuidado: debe mapear a un status HTTP claro.

2. **Usá helpers de acceso de workspace**

   * lectura: `resolve_workspace_for_read`
   * escritura: `resolve_workspace_for_write`
   * mantiene consistencia de ACL + visibility.

3. **Mantené soft delete como default**

   * si querés delete físico, que sea un caso de uso separado (ej: `purge_document.py`) con guardias y/o job.

4. **Metadata: normalización siempre en Application**

   * no delegar a HTTP “porque ya valida”.
   * Application protege invariantes incluso si el caller es el worker.

5. **Cableado y tests**

   * registrar en `app/container.py`.
   * unit tests con repos fake.
   * integration tests con Postgres + storage adapter si aplica.

---

## 🆘 Troubleshooting

* **Síntoma:** `NOT_FOUND` con un documento que “existe”

  * **Causa probable:** `workspace_id` no coincide o el actor no tiene acceso.
  * **Solución:** confirmar que el documento pertenece a ese workspace; revisar policy/ACL en `workspace_access.py`.

* **Síntoma:** metadata no se actualiza o se “pierden” tags

  * **Causa probable:** normalización (dedup/trim) o campos no editables.
  * **Solución:** revisar `update_document_metadata.py` (lista de campos permitidos y reglas de tags).

* **Síntoma:** descarga falla con `storage_key` faltante

  * **Causa probable:** documento creado sin registro de storage o inconsistencia de estado.
  * **Solución:** revisar ingesta/upload (quién setea `storage_key`) y `download_document.py` (cómo resuelve la llave).

* **Síntoma:** delete “no borra”

  * **Causa probable:** es soft delete (estado archivado) por diseño.
  * **Solución:** verificar estado del documento; si necesitás purge físico, crear caso de uso aparte con política explícita.

---

## 🔎 Ver también

* [Use cases hub](../README.md)
* [Workspace access helper](../workspace/workspace_access.py)
* [Chat (RAG) usa DocumentError](../chat/README.md)
* [Infrastructure storage](../../../infrastructure/storage/README.md)
* [Infrastructure repositories](../../../infrastructure/repositories/README.md)
