# HTTP Adapter Layer

Esta carpeta contiene la implementación de la API REST usando **FastAPI**.
En términos de _Clean Architecture_, esta es una capa de **Interface Adapters**.

## 🎯 Responsabilidad

Su única responsabilidad es **adaptar** el mundo exterior (HTTP, JSON) al mundo interior (Casos de Uso, Entidades).

1.  **Recibir**: Requests HTTP, validar JSON, headers y query params.
2.  **Orquestar**: Invocar al Caso de Uso apropiado (`application/usecases`).
3.  **Responder**: Convertir el resultado del Caso de Uso (Entidades/DTOs) a JSON HTTP (RFC 7807).

## 📂 Estructura

| Archivo/Carpeta    | Descripción                                                                    |
| :----------------- | :----------------------------------------------------------------------------- |
| `router.py`        | **Root Router**. Compone todos los sub-routers. Punto de entrada de FastAPI.   |
| `dependencies.py`  | **DI Helpers**. Inyección de dependencias común (Use Cases, Repos, Auth).      |
| `error_mapping.py` | **Traductor**. Convierte `DomainError` -> `HTTPException` (4xx/5xx).           |
| `routers/`         | **Controladores**. Agrupados por Bounded Context (_Workspaces, Documents..._). |
| `schemas/`         | **DTOs**. Modelos Pydantic de Request y Response.                              |
| `routes.py`        | _(Legacy/Shim)_ Módulo de compatibilidad temporal.                             |

## 🧩 Patrones Clave

### 1. No Business Logic

Los routers **NO** contienen lógica de negocio. Solo validación de entrada y transformación de salida.

- ❌ `if document.status == 'ready': ...`
- ✅ `use_case.execute(...)`

### 2. Error Handling Centralizado

No hagas `try/except` ad-hoc. Usa `error_mapping.py` para traducir errores de dominio de forma consistente.

### 3. Schemas Segregados

Los modelos de Pydantic (`schemas/`) están desacoplados de las Entidades de Dominio (`domain/entities.py`). Esto permite cambiar la API sin romper el dominio y viceversa.
