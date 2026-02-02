# Backend Application (paquete `app`)

## 🎯 Misión

Este paquete es el **source root** del backend: acá vive **todo el código ejecutable** y versionado que permite correr el servicio en sus dos modos principales:

* **API HTTP** (FastAPI sobre ASGI)
* **Worker asíncrono** (RQ sobre Redis)

Si `apps/backend/` es el “taller” (build, tooling, tests, migraciones), `app/` es el **motor**: define las reglas del producto, cómo se orquestan, y cómo se conectan con el mundo exterior.

**Qué SÍ hace**

* Define el **núcleo de negocio** (entidades y contratos) en `domain/`.
* Orquesta el comportamiento del sistema como **casos de uso** en `application/`.
* Implementa adaptadores a servicios externos (DB/queue/storage/LLM/parsers) en `infrastructure/`.
* Expone puntos de entrada (HTTP y worker) en `interfaces/`, `api/` y `worker/`.
* Centraliza el cableado de dependencias en `container.py` (composition root).

**Qué NO hace (y por qué)**

* No contiene scripts operativos de repo ni tareas de CI: eso vive en `../scripts/`.

  * **Razón:** mantener el runtime separado del tooling evita imports “accidentales” y dependencias circulares.
* No contiene pruebas: eso vive en `../tests/`.

  * **Razón:** tests dependen de “cómo se usa” el runtime, pero el runtime no debe depender de tests.

Analogía breve: `app/` es el **motor armado** (piezas + cableado + puntos de entrada). El “taller” (build/migraciones/tests) vive afuera.

---

## 🗺️ Mapa del territorio

| Recurso              | Tipo              | Responsabilidad (en humano)                                                                |
| :------------------- | :---------------- | :----------------------------------------------------------------------------------------- |
| 📁 `api/`            | 📁 Carpeta        | Composición de FastAPI: creación de app, lifespan y endpoints operativos (health/metrics). |
| 📁 `application/`    | 📁 Carpeta        | Casos de uso y orquestación: define “qué hace el sistema” a nivel de flujo.                |
| 🐍 `audit.py`        | 🐍 Archivo Python | Emisión de eventos de auditoría best-effort (registro de acciones relevantes).             |
| 🐍 `container.py`    | 🐍 Archivo Python | Composition root: factories, singletons y selección de implementaciones (prod/test).       |
| 🐍 `context.py`      | 🐍 Archivo Python | Contexto de ejecución (request_id, tracing, metadatos por request/job).                    |
| 📁 `crosscutting/`   | 📁 Carpeta        | Utilidades transversales: config, logging, errores, métricas, helpers compartidos.         |
| 📁 `domain/`         | 📁 Carpeta        | Núcleo puro: entidades, value objects, contratos (puertos) y reglas estables.              |
| 📁 `identity/`       | 📁 Carpeta        | Autorización: roles, permisos, políticas de acceso y validaciones.                         |
| 📁 `infrastructure/` | 📁 Carpeta        | Adaptadores salientes: DB, storage, colas, parsers, LLMs, prompts infra.                   |
| 📁 `interfaces/`     | 📁 Carpeta        | Adaptadores entrantes: HTTP (routers/schemas) y mapeo DTO ↔ application.                   |
| 🐍 `jobs.py`         | 🐍 Archivo Python | Entrypoints estables para jobs RQ (funciones invocables por el worker).                    |
| 🐍 `main.py`         | 🐍 Archivo Python | Entrypoint ASGI estable (`app.main:app`) para Uvicorn/Gunicorn.                            |
| 📁 `prompts/`        | 📁 Carpeta        | Assets de prompts/policy (archivos .md versionados, consumidos por `PromptLoader`).        |
| 📄 `README.md`       | 📄 Documento      | Portada técnica del paquete `app/` (este documento).                                       |
| 📁 `worker/`         | 📁 Carpeta        | Proceso worker RQ + health/metrics (ejecuta jobs fuera del request).                       |

---

## ⚙️ ¿Cómo funciona por dentro?

Este paquete está organizado siguiendo **Clean Architecture**: separar responsabilidades para que el negocio sea testable, mantenible y resistente a cambios de infraestructura.

### 1) Conceptos mínimos (para leer el repo sin perderse)

* **Domain**: “qué es” el sistema y qué reglas son estables. No sabe nada de FastAPI, Postgres o Redis.
* **Application**: “qué hace” el sistema como flujo: recibe una intención, valida, orquesta y produce un resultado. Depende de contratos del Domain.
* **Infrastructure**: “cómo” se habla con el mundo real: DB, colas, storage, proveedores LLM, parsers. Implementa puertos del Domain.
* **Interfaces**: adaptadores de entrada: HTTP (request/response), DTOs y mapping hacia Application.

### 2) Entradas principales (API y Worker)

**Entrada A — API HTTP (FastAPI)**

* El servidor ASGI (por ejemplo `uvicorn`) importa `app.main:app`.
* `app.main` expone un objeto ASGI estable y liviano (sin side-effects grandes).
* La composición concreta de FastAPI se hace en `app/api/` (incluye lifecycle/lifespan).

**Entrada B — Worker (RQ)**

* El worker corre como proceso separado (no comparte ciclo de vida con HTTP).
* Consume jobs desde Redis y ejecuta funciones definidas como entrypoints en `jobs.py`.
* El worker también expone endpoints operativos (health/metrics) para monitoreo.

### 3) Flujo end-to-end (request típico)

**Input → Proceso → Output**

* **Input:** request HTTP (router) o job en cola (worker).
* **Proceso:**

  1. **Interfaces (HTTP)** validan el input con schemas (Pydantic) y lo transforman a comandos/DTOs de Application.
  2. **Application (use cases)** orquesta el flujo: valida reglas, llama puertos del Domain y decide el resultado.
  3. **Infrastructure** realiza IO real: DB/Redis/storage/LLM/parsing.
  4. **Crosscutting** aporta preocupaciones transversales: logs, métricas, errores tipados, config.
* **Output:**

  * HTTP: respuesta JSON/streaming + errores normalizados.
  * Worker: side-effects (persistencia, storage), métricas y logs.

### 4) ¿Qué significa ASGI aquí?

ASGI es el estándar para aplicaciones web asíncronas en Python.

* **FastAPI** construye la app.
* **Uvicorn/Gunicorn** ejecutan la app.
* `app.main:app` es el “objeto que el servidor ejecuta”.

### 5) Tecnologías principales (explicadas en contexto)

* **FastAPI**: framework HTTP; aporta tipado, validación y OpenAPI.
* **Pydantic**: validación/serialización de DTOs (request/response).
* **PostgreSQL + pgvector**: persistencia transaccional + embeddings vectoriales para RAG.
* **psycopg**: driver de Postgres para ejecutar SQL (sin ORM).
* **Redis + RQ**: cola simple para trabajos asíncronos (evita bloquear requests con tareas pesadas).

📌 Para detalle por capa:

* Application → [`application/README.md`](./application/README.md)
* Domain → [`domain/README.md`](./domain/README.md)
* Infrastructure → [`infrastructure/README.md`](./infrastructure/README.md)
* HTTP → [`interfaces/api/http/README.md`](./interfaces/api/http/README.md)

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Source Root del runtime (capas internas + wiring).
* **Recibe órdenes de:**

  * Servidor ASGI (API): `app.main:app`.
  * Worker RQ: proceso separado bajo `worker/`.
  * Tooling interno (cuando aplica): scripts o tests que importan `fastapi_app`.
* **Llama a:**

  * Domain, Application, Infrastructure e Interfaces.
  * Servicios externos (DB/Redis/LLM) a través de adapters en Infrastructure.
* **Contratos y límites (reglas fuertes):**

  * `domain/` no importa `infrastructure/`.
  * `application/` orquesta vía puertos (interfaces) definidos en `domain/`.
  * `interfaces/` adapta HTTP (DTOs, status codes) y delega en Application.
  * `infrastructure/` implementa puertos y no contiene reglas de negocio.

---

## 👩‍💻 Guía de uso (Snippets)

### Smoke test HTTP (FastAPI)

Este snippet es útil para tests rápidos o debugging local.

```python
from fastapi.testclient import TestClient
from app.api.main import fastapi_app

client = TestClient(fastapi_app)
resp = client.get("/healthz")
assert resp.status_code == 200
```

### Entrypoint ASGI (lo que corre uvicorn)

```python
from app.main import app as asgi_app

assert callable(asgi_app)
```

---

## 🧩 Cómo extender sin romper nada

1. **Caso de uso primero**: agregá/extendé comportamiento en `application/usecases/`.
2. **Contratos en Domain**: si necesitás IO nuevo, definí el puerto (repository/service) en `domain/`.
3. **Implementación en Infrastructure**: creá el adapter concreto (Postgres/Redis/Storage/LLM) en `infrastructure/`.
4. **Cableado en `container.py`**: registrá la implementación correcta (prod vs tests).
5. **Exposición en HTTP**: agregá router en `interfaces/api/http/routers/` y DTOs en `schemas/`.
6. **Observabilidad**: asegurate de loggear/meter métricas desde Crosscutting si aplica.
7. **Tests**:

   * unit para Domain/Application puro
   * integration para DB/Redis
   * e2e para flujos completos

---

## 🆘 Troubleshooting

* **Síntoma:** `ModuleNotFoundError: No module named 'app'`

  * **Causa probable:** ejecución desde un directorio incorrecto.
  * **Qué mirar:** ejecutar desde `apps/backend/` o revisar `PYTHONPATH`/WORKDIR.

* **Síntoma:** use cases usan repos in-memory inesperados

  * **Causa probable:** el entorno está en modo test o configuración selecciona adapters fake.
  * **Qué mirar:** selección en `container.py` y variables de entorno relacionadas (p.ej. `APP_ENV`).

* **Síntoma:** pool/recursos no inicializados (errores al usar DB)

  * **Causa probable:** no se ejecutó el ciclo de vida (lifespan) de FastAPI.
  * **Qué mirar:** composición en `api/` (lifespan) y la inicialización de DB/clients.

---

## 🔎 Ver también

* [Backend root](../README.md)
* [API composition](./api/README.md)
* [Application layer](./application/README.md)
* [Domain layer](./domain/README.md)
* [Infrastructure layer](./infrastructure/README.md)
* [Interfaces HTTP](./interfaces/api/http/README.md)
* [Worker](./worker/README.md)
