# Layer: Crosscutting (Shared Utilities)

## 🎯 Misión

Esta carpeta contiene módulos transversales que son utilizados por **todas** las capas del sistema.
Aquí viven las "herramientas" que no pertenecen a ningún dominio de negocio específico, pero son esenciales para que la aplicación funcione de manera profesional.

**Qué SÍ hace:**

- Carga y valida configuración (`config.py`).
- Gestiona Logging estructurado (`logger.py`).
- Implementa métricas y observabilidad (`metrics.py`, `tracing.py`).
- Define middlewares genéricos (`middleware.py`, `rate_limit.py`, `security.py`).
- Estandariza errores HTTP (`error_responses.py`, `exceptions.py`).

**Qué NO hace:**

- No contiene lógica de negocio (Use Cases).
- No accede a la base de datos (excepto para cosas muy puntuales de infra).

**Analogía:**
Son los **Cimientos y Servicios Públicos** del edificio (Agua, Luz, Gas). Están en todas partes, en todas las habitaciones, pero no son "la habitación" en sí.

## 🗺️ Mapa del territorio

| Recurso              | Tipo       | Responsabilidad (en humano)                                      |
| :------------------- | :--------- | :--------------------------------------------------------------- |
| `config.py`          | 🐍 Archivo | Carga variables de entorno en un objeto `Settings` tipado.       |
| `error_responses.py` | 🐍 Archivo | Modelos para respuestas de error estandarizadas (RFC7807).       |
| `exceptions.py`      | 🐍 Archivo | Excepciones base del sistema (`AppException`).                   |
| `logger.py`          | 🐍 Archivo | Configuración centralizada de logs (JSON en prod, color en dev). |
| `metrics.py`         | 🐍 Archivo | Exposición de métricas Prometheus.                               |
| `middleware.py`      | 🐍 Archivo | Middlewares HTTP varios (Contexto, Body Limit).                  |
| `pagination.py`      | 🐍 Archivo | Modelos y lógica para paginación de listas.                      |
| `rate_limit.py`      | 🐍 Archivo | Lógica y middleware de limitación de tasa (Rate Limiting).       |
| `security.py`        | 🐍 Archivo | Headers de seguridad (CSP, HSTS) y utilidades crypto.            |
| `streaming.py`       | 🐍 Archivo | Helpers para respuestas en streaming (SSE/NDJSON).               |
| `timing.py`          | 🐍 Archivo | Decoradores para medir tiempo de ejecución.                      |
| `tracing.py`         | 🐍 Archivo | Integración básica de tracing distribuido.                       |

## ⚙️ ¿Cómo funciona por dentro?

### Configuración (`config.py`)

Usamos **Pydantic Settings**.

1.  Lee variables de entorno (`.env` o sistema).
2.  Valida tipos (ej. puerto debe ser int).
3.  Expone un singleton `get_settings()` cacheado.

### Logging (`logger.py`)

Intercepamos el logging estándar de Python y lo redirigimos para que salga estructurado (con `extra={...}`).
Soporta inyección de `request_id` context-aware.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Shared Kernel / Cross-cutting Concerns.
- **Recibe órdenes de:** TODO el sistema (API, Domain, Infra, App).
- **Llama a:** Librerías base (Stdlib, Pydantic, Prometheus client).
- **Límites:** **NUNCA** debe importar de `application`, `interfaces` o `infrastructure` (para evitar ciclos). Debe ser autodependiente.

## 👩‍💻 Guía de uso (Snippets)

### Usar Configuración

```python
from app.crosscutting.config import get_settings

settings = get_settings()
print(settings.database_url)
```

### Usar Logger

```python
from app.crosscutting.logger import logger

try:
    process_data()
except Exception as e:
    logger.error("Error procesando datos", extra={"doc_id": "123", "error": str(e)})
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevas Variables de Entorno:** Agrégalas a la clase `Settings` en `config.py` con su tipo y valor por defecto.
2.  **Excepciones:** Hereda siempre de `AppException` (en `exceptions.py`) para que los handlers globales las capturen bien.

## 🆘 Troubleshooting

- **Síntoma:** "ValidationError: field required" al iniciar.
  - **Causa:** Falta una variable de entorno obligatoria en `.env`.
- **Síntoma:** Circular Import Error.
  - **Causa:** Probablemente importaste algo de `application` dentro de `crosscutting`. Revisa tus imports.

## 🔎 Ver también

- [API (Consumidor principal)](../api/README.md)
