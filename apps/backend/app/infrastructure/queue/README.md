# queue
Como una **bandeja de tareas**: encola trabajos en Redis para que el worker los ejecute.

## 🎯 Misión

Este módulo implementa el adaptador de cola basado en **RQ** para encolar el procesamiento asíncrono de documentos. Su responsabilidad es **recibir datos mínimos del caso de uso**, validar configuración y rutas de jobs (fail-fast), y delegar el trabajo a RQ/Redis devolviendo un `job_id` rastreable.

Recorridos rápidos por intención:

* **Quiero ver el adapter que implementa el puerto del dominio** → `rq_queue.py`
* **Quiero ver qué job paths/colas están permitidos** → `job_paths.py`
* **Quiero ver la validación de dotted paths importables** → `import_utils.py`
* **Quiero ver errores tipados del adapter** → `errors.py`
* **Quiero ver cómo se usa desde ingesta** → `../../application/usecases/ingestion/README.md`

### Qué SÍ hace

* Encola jobs de procesamiento con RQ (Redis como backend).
* Valida **dotted paths importables** de jobs antes de encolar (fail-fast).
* Tipifica errores de configuración y de enqueue para diagnóstico consistente.
* Expone una fachada estable desde `__init__.py` para imports simples.

### Qué NO hace (y por qué)

* No ejecuta los jobs.

- **Razón:** la ejecución pertenece al **worker**.
- **Impacto:** si la cola encola pero “no pasa nada”, el problema suele estar en el worker (apagado, mal configurado o sin importar el job).
* No contiene lógica de negocio.

- **Razón:** el negocio vive en Domain/Application.
- **Impacto:** este módulo solo traduce “encolar” → “RQ/Redis”, sin reglas de permisos, estados o decisiones.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :---------------- | :------------- | :----------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Facade del adaptador de cola (exports públicos). |
| `errors.py` | Archivo Python | Errores tipados de cola (config inválida, enqueue fallido, job path inválido). |
| `import_utils.py` | Archivo Python | Validación de dotted paths importables (fail-fast antes de encolar). |
| `job_paths.py` | Archivo Python | Catálogo de job paths y nombres de cola (constantes estables). |
| `rq_queue.py` | Archivo Python | Adapter RQ que implementa `DocumentProcessingQueue` del dominio. |
| `README.md` | Documento | Portada + guía operativa de la cola RQ. |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output.

* **Input:** `document_id` y `workspace_id` (y/o metadata mínima) que llegan desde el caso de uso (por ejemplo, upload).
* **Proceso:**

  1. `RQDocumentProcessingQueue` valida su configuración (Redis, nombre de cola, timeouts si aplica).
  2. Antes de encolar, valida que el job a ejecutar sea **importable** (`import_utils.is_importable_dotted_path(...)`) usando los paths definidos en `job_paths.py`.
  3. Encola el trabajo en RQ (Redis), pasando args/kwargs del job.
  4. Si falla Redis/RQ, lanza un error tipado de `errors.py` (para que Application pueda reaccionar con un error consistente).
* **Output:** `job_id` (o equivalente) para tracking, o error tipado.

Conceptos mínimos en contexto:

* **RQ:** encola un “job” con un callable (por dotted path) y argumentos; el worker lo consume.
* **Dotted path importable:** asegura que el worker pueda importar exactamente el callable declarado (evita jobs que fallan al arrancar).

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Infrastructure Adapter (queue).
* **Recibe órdenes de:** Application (use cases de ingesta, por ejemplo upload).
* **Llama a:** RQ / Redis.
* **Contratos y límites:**

- Implementa `DocumentProcessingQueue` del dominio.
- No importa repositorios ni casos de uso.
- No define jobs acá: solo referencia paths definidos en `job_paths.py` y ejecutados por el worker.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from redis import Redis
from app.infrastructure.queue import RQDocumentProcessingQueue, RQQueueConfig

queue = RQDocumentProcessingQueue(redis=Redis.from_url("redis://localhost:6379"), config=RQQueueConfig())
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from uuid import UUID

job_id = queue.enqueue_document_processing(document_id=UUID("..."), workspace_id=UUID("..."))
print(job_id)
```

```python
# Por qué: deja visible el flujo principal.
from app.infrastructure.queue.job_paths import PROCESS_DOCUMENT_JOB_PATH
print(PROCESS_DOCUMENT_JOB_PATH)
```

## 🧩 Cómo extender sin romper nada
- Definí el job en `app/worker/jobs.py` y registrá el path en `job_paths.py`.
- Mantené validación de path con `is_importable_dotted_path`.
- Cableá el adapter en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/infrastructure/`, integration con Redis en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `Job path no importable`.
- **Causa probable:** path incorrecto o job no exportado.
- **Dónde mirar:** `job_paths.py` y `app/worker/jobs.py`.
- **Solución:** corregir path o export.
- **Síntoma:** enqueue falla.
- **Causa probable:** Redis caído o URL inválida.
- **Dónde mirar:** `REDIS_URL` y logs.
- **Solución:** levantar Redis o corregir URL.
- **Síntoma:** jobs no se procesan.
- **Causa probable:** worker apagado o escuchando otra cola.
- **Dónde mirar:** `app/worker/worker.py`.
- **Solución:** alinear nombre de cola.
- **Síntoma:** timeouts de job.
- **Causa probable:** `job_timeout_seconds` bajo.
- **Dónde mirar:** `RQQueueConfig`.
- **Solución:** ajustar configuración.

## 🔎 Ver también
- `../../worker/README.md`
- `../../application/usecases/ingestion/README.md`
- `../README.md`
