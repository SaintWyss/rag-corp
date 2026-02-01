# Worker Layer (RQ)

Esta capa implementa el procesamiento asíncrono de tareas pesadas (ingesta de documentos, generación de embeddings) utilizando **Redis Queue (RQ)**.

## 🎯 Responsabilidades

- **Procesamiento Asíncrono**: Ejecutar casos de uso que tardan demasiado para ser una request HTTP sincrónica.
- **Aislamiento**: Correr en un proceso separado para no bloquear el API.
- **Resiliencia**: Manejo de reintentos (vía RQ) y reporte de fallos.
- **Observabilidad**: Exponer sus propios endpoints de health y métricas.

## 📂 Estructura

| Archivo            | Rol             | Descripción                                                                                                      |
| :----------------- | :-------------- | :--------------------------------------------------------------------------------------------------------------- |
| `worker.py`        | **Entrypoint**  | El `main` del proceso. Inicializa Redis, DB Pool y arranca el loop de RQ.                                        |
| `jobs.py`          | **Tasks**       | Definición de las funciones ejecutables (`process_document_job`). Actúa como adaptador entre RQ y los Use Cases. |
| `worker_server.py` | **Ops Server**  | Servidor HTTP liviano (`http.server`) para exponer `/healthz` y `/metrics`.                                      |
| `worker_health.py` | **Diagnostics** | Lógica de chequeo de conectividad (Redis/DB) y CLI para Docker healthcheck.                                      |

## 🚀 Flujo de Ejecución

1.  **Bootstrap**: `worker.py` valida conexión a Redis y DB.
2.  **Server Ops**: Levanta un thread con `worker_server` en puerto 8001 (default).
3.  **Loop**: `rq.Worker` comienza a escuchar en la cola `documents`.
4.  **Job**: Al recibir un mensaje, invoca `jobs.process_document_job`.
    - Parsea argumentos (UUIDs).
    - Setea **Context Vars** (Request ID) para trazas distribuidas.
    - Construye el Use Case (`ProcessUploadedDocumentUseCase`) con dependencias frescas.
    - Ejecuta y reporta resultado.

## 🛡️ Resilience & Safety

- **Fail-Fast**: El worker no arranca si Redis no responde.
- **Graceful Shutdown**: Intercepta SIGINT/SIGTERM para terminar el job actual y cerrar conexiones a DB.
- **Context Isolation**: Cada job limpia su contexto (`clear_context`) al terminar para evitar data leaks.

## 📊 Métricas y Health

El worker expone un puerto HTTP (default 8001):

- `GET /healthz`: Liveness (¿estoy vivo?).
- `GET /readyz`: Readiness (¿tengo DB y Redis?).
- `GET /metrics`: Métricas Prometheus (Jobs procesados, tiempo de ejecución). **Requiere Auth** si está configurado.
