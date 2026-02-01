# Infrastructure Queue Layer

## 🎯 Propósito y Rol

Este paquete (`infrastructure/queue`) implementa el adaptador para **procesamiento asíncrono** usando **Redis Queue (RQ)**. Su responsabilidad es desacoplar la recepción de documentos (rápida) de su procesamiento pesado (Embeddings, Chunking).

---

## 🧩 Componentes Principales

### 1. El Adaptador (Queue)

| Archivo        | Rol         | Descripción                                                                               |
| :------------- | :---------- | :---------------------------------------------------------------------------------------- |
| `rq_queue.py`  | **Adapter** | Implementa la interfaz `DocumentProcessingQueue` del dominio. Encola mensajes en Redis.   |
| `job_paths.py` | **Config**  | Centraliza las rutas de los jobs ("dotted paths") para evitar errores de typo en runtime. |

### 2. Seguridad y Validación

| Archivo           | Rol            | Descripción                                                                        |
| :---------------- | :------------- | :--------------------------------------------------------------------------------- |
| `import_utils.py` | **Validator**  | Verifica que los jobs sean importables antes de encolar. Fail-Fast.                |
| `errors.py`       | **Exceptions** | Excepciones tipadas (`QueueConfigurationError`) para problemas de infraestructura. |

---

## 🛠️ Arquitectura y Patrones

### Dependency Injection (DI) Real

A diferencia de implementaciones naive, aquí **no creamos clientes Redis** dentro de la cola.

- El `Redis` client se inyecta desde fuera (`container.py`).
- **Beneficio:** Permite compartir la conexión (Pool) con otros componentes (Caché, Rate Limiter) y facilita el mocking en tests.

### Fail-Fast Configuration

El sistema valida que:

1.  La URL de Redis exista.
2.  El path del job (`app.worker.jobs...`) sea importable.

Si algo está mal, la aplicación falla al arrancar (o al primer uso), en lugar de dejar trabajos "zombies" en la cola que nunca se procesan.

---

## 🚀 Guía de Uso

### Configuración (Environment)

| Variable              | Default     | Descripción                                      |
| :-------------------- | :---------- | :----------------------------------------------- |
| `REDIS_URL`           | _Requerido_ | URL de conexión (ej: `redis://localhost:6379/0`) |
| `DOCUMENT_QUEUE_NAME` | `documents` | Nombre de la lista en Redis                      |
| `RETRY_MAX_ATTEMPTS`  | `3`         | Reintentos automáticos si el worker falla        |

### Flujo de Datos

1.  **API**: Recibe Upload -> Llama a `queue.enqueue_document_processing(doc_id)`.
2.  **Redis**: Guarda el mensaje `{"job": "app.worker.jobs...", "args": [doc_id]}`.
3.  **Worker**: Proceso separado (`app/worker/main.py`) lee de Redis y ejecuta el código.

### Estructura del Job

El job debe ser puro e importar sus dependencias dentro de la función (Lazy Import) para evitar ciclos con el contenedor.

```python
# app/worker/jobs.py
def process_document_job(doc_id: str, ...):
    # Lazy imports para evitar ciclos
    from ..container import get_use_case
    use_case = get_use_case()
    use_case.execute(doc_id)
```
