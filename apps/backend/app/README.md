# RAG Corp Backend Application

Bienvenido al núcleo de la aplicación backend de RAG Corp.
Esta estructura sigue los principios de **Clean Architecture** (Arquitectura Hexagonal) para garantizar mantenibilidad, testabilidad y desacoplamiento.

## 🗺️ Mapa de Navegación

| Capa / Directorio     | Descripción                                                                                        | Dependencias Permitidas       |
| :-------------------- | :------------------------------------------------------------------------------------------------- | :---------------------------- |
| **`domain/`**         | **Núcleo Puro**. Entidades de negocio, reglas y puertos (interfaces). No sabe nada de DB ni API.   | Ninguna (solo stdlib).        |
| **`application/`**    | **Casos de Uso**. Orquesta la lógica de aplicación implementando los requerimientos del usuario.   | `domain`, `crosscutting`.     |
| **`infrastructure/`** | **Adaptadores de Salida**. Implementaciones concretas de puertos (Postgres, S3, Redis, Google AI). | `domain`, librerías externas. |
| **`interfaces/`**     | **Adaptadores de Entrada**. API HTTP (FastAPI), CLI, etc.                                          | `application`, `domain`.      |
| **`api/`**            | **Composition Root**. Configuración de arranque, cableado de dependencias y entrypoint `main.py`.  | Todas.                        |
| **`worker/`**         | **Procesamiento Async**. Workers de RQ para tareas en segundo plano.                               | `application`, `container`.   |
| **`crosscutting/`**   | **Transversal**. Utilidades compartidas (Logger, Config, Metrics, Middlewares).                    | Ninguna (idealmente).         |

## 🏗️ Archivos Clave en la Raíz

- **`container.py`**: **Dependency Injection Container**. Aquí se instancias y conectan todas las piezas (Repositories -> Use Cases). Es el único lugar donde se permite el acoplamiento fuerte para el cableado.
- **`main.py`**: Re-exporta la instancia `app` de FastAPI para servidores ASGI (Uvicorn/Gunicorn).
- **`audit.py`**: Helper global para emisión de eventos de auditoría (best-effort).
- **`context.py`**: Gestión de ContextVars (Request ID, Trace ID) para observabilidad distribuida.
- **`jobs.py`**: Fachada estable para los jobs de RQ (evita roturas si se mueve código interno).

## 🧩 Flujo de una Request (Happy Path)

1.  **Request HTTP** llega a `api/main.py`.
2.  Middlewares (CORS, Context) procesan la entrada.
3.  Router (`interfaces/api/http/router.py`) despacha al controlador correspondiente.
4.  Controlador (`interfaces/.../routers/*.py`) invoca un **Caso de Uso**.
5.  **Caso de Uso** (`application/usecases/...`) obtiene datos vía **Puertos** (`domain/repositories`).
6.  **Container** (`container.py`) inyecta la implementación concreta (`infrastructure/db`) en runtime.
7.  El repositorio ejecuta SQL y retorna **Entidades de Dominio**.
8.  El caso de uso aplica reglas de negocio y devuelve un resultado.
9.  El controlador convierte el resultado a **DTO de Respuesta** (JSON).

## 🧪 Testing

La arquitectura facilita el testing unitario:

- **Dominio**: Tests puros sin mocks.
- **Aplicación**: Tests unitarios mockeando los repositorios (fácil gracias a DI).
- **Infraestructura**: Tests de integración con contenedores reales (Postgres/Redis).

---

_Para más detalles, consulta el README específico dentro de cada subdirectorio._
