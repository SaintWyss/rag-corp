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

  * **Razón:** la ejecución pertenece al **worker**.
  * **Impacto:** si la cola encola pero “no pasa nada”, el problema suele estar en el worker (apagado, mal configurado o sin importar el job).
* No contiene lógica de negocio.

  * **Razón:** el negocio vive en Domain/Application.
  * **Impacto:** este módulo solo traduce “encolar” → “RQ/Redis”, sin reglas de permisos, estados o decisiones.

## 🗺️ Mapa del territorio

| Recurso           | Tipo           | Responsabilidad (en humano)                                                    |
| :---------------- | :------------- | :----------------------------------------------------------------------------- |
| `__init__.py`     | Archivo Python | Facade del adaptador de cola (exports públicos).                               |
| `errors.py`       | Archivo Python | Errores tipados de cola (config inválida, enqueue fallido, job path inválido). |
| `import_utils.py` | Archivo Python | Validación de dotted paths importables (fail-fast antes de encolar).           |
| `job_paths.py`    | Archivo Python | Catálogo de job paths y nombres de cola (constantes estables).                 |
| `rq_queue.py`     | Archivo Python | Adapter RQ que implementa `DocumentProcessingQueue` del dominio.               |
| `README.md`       | Documento      | Portada + guía operativa de la cola RQ.                                        |

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

  * Implementa `DocumentProcessingQueue` del dominio.
  * No importa repositorios ni casos de uso.
  * No define jobs acá: solo referencia paths definidos en `job_paths.py` y ejecutados por el worker.

## 👩‍💻 Guía de uso (Snippets)

### 1) Construir el adapter (runtime)

```python
from redis import Redis

from app.infrastructure.queue import RQDocumentProcessingQueue, RQQueueConfig

queue = RQDocumentProcessingQueue(
    redis=Redis.from_url("redis://localhost:6379"),
    config=RQQueueConfig(),
)
```

### 2) Encolar procesamiento (desde Application)

```python
from uuid import UUID

job_id = queue.enqueue_document_processing(
    document_id=UUID("00000000-0000-0000-0000-000000000000"),
    workspace_id=UUID("11111111-1111-1111-1111-111111111111"),
)
print(job_id)
```

### 3) Validar un job path (fail-fast)

```python
from app.infrastructure.queue.import_utils import is_importable_dotted_path
from app.infrastructure.queue.job_paths import PROCESS_DOCUMENT_JOB_PATH

assert is_importable_dotted_path(PROCESS_DOCUMENT_JOB_PATH)
```

### 4) Referenciar paths estables (compatibilidad)

```python
from app.infrastructure.queue.job_paths import PROCESS_DOCUMENT_JOB_PATH

print(PROCESS_DOCUMENT_JOB_PATH)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo job:** definí el callable en el worker (`../../worker/`).
2. **Registrar el dotted path:** agregalo en `job_paths.py` como constante estable.
3. **Mantener fail-fast:** validá el path con `is_importable_dotted_path(...)` antes de encolar.
4. **Config:** si agregás nombre de cola nuevo o setting, documentalo y exponerlo desde la config del adapter.
5. **Cableado:** asegurá que el container inyecte este adapter donde se construye `DocumentProcessingQueue`.
6. **Tests:**

   * unit: paths importables + errores tipados.
   * integración: encolar contra Redis real y verificar `job_id`.

## 🆘 Troubleshooting

* **Job path no importable** → el callable no existe o el path cambió → revisar `job_paths.py`, `import_utils.py`, `../../worker/` → corregir path o exportar el callable.
* **Enqueue falla (Redis/RQ)** → Redis caído o URL inválida → revisar `REDIS_URL`, red y `rq_queue.py` → levantar Redis/corregir config.
* **Jobs se encolan pero no se procesan** → worker apagado o escuchando otra cola → revisar `../../worker/README.md` y config de cola → iniciar worker y alinear cola.
* **Job falla al ejecutar** → import/dependencia faltante en worker → revisar logs/traceback → corregir imports o instalar deps.
* **Jobs lentos/cola crece** → pocos workers o job pesado → revisar métricas/logs → escalar workers u optimizar pipeline.

## 🔎 Ver también

* `../../worker/README.md` (ejecución de jobs)
* `../../application/usecases/ingestion/README.md` (dónde se encola)
* `../README.md` (índice de infraestructura, si aplica)
