# Crosscutting Layer

## 🎯 Propósito y Rol

Este paquete (`app/crosscutting`) encapsula las preocupaciones **transversales** de la aplicación.
Implementa patrones tipo AOP (Aspect Oriented Programming) de forma manual y explícita, asegurando que todos los subsistemas compartan:

- Observabilidad (Logging, Metrics, Tracing).
- Seguridad Base (Rate Limit, Body Limits).
- Configuración Runtime (Settings).
- Manejo de Errores (Taxonomía, RFC7807).

---

## 🧩 Componentes Principales

| Archivo         | Rol                | Descripción                                                                                                   |
| :-------------- | :----------------- | :------------------------------------------------------------------------------------------------------------ |
| `config.py`     | **Singleton**      | Carga y valida variables de entorno (`.env`). Aplica validaciones de seguridad tipo fail-fast.                |
| `logger.py`     | **Observabilidad** | Logger estructurado (JSON). Redacta automáticamente secretos (PII/Credenciales). Inyecta `request_id`.        |
| `metrics.py`    | **Observabilidad** | Cliente Prometheus (opcional). Define métricas de negocio (RAG stages) e infraestructura (DB, Worker).        |
| `tracing.py`    | **Observabilidad** | Cliente OpenTelemetry (opcional). Inyecta `trace_id` en logs para correlación distribuida.                    |
| `exceptions.py` | **Contrato**       | Jerarquía de excepciones internas (`RAGError`). Garantiza códigos de error estables (`error_code`).           |
| `middleware.py` | **Pipeline**       | Interceptores HTTP. Manejan Request Context (`request_id`) y protegen contra payloads gigantes (`BodyLimit`). |
| `rate_limit.py` | **Protección**     | Algoritmo Token Bucket en memoria con limpieza automática (TTL). Protege contra abuso por IP o API Key.       |

---

## 🛠️ Arquitectura y Decisiones de Diseño

### 1. Dependencias Opcionales (Fail-Safe)

Sistemas como `metrics.py` y `tracing.py` están diseñados para **no romper** la aplicación si faltan librerías (`prometheus_client`, `opentelemetry`).

- **Beneficio**: Permite despliegues ligeros o entornos de test aislados.

### 2. Context Propagation

Usamos `contextvars` (en `app/context.py`) para propagar `request_id`, `trace_id` y `user_id` a través de capas asíncronas sin ensuciar la firma de los métodos.

- `logger.py` lee estas variables automáticamente.

### 3. Seguridad por Defecto

- **Logs**: `_Redactor` filtra claves como `password`, `api_key` antes de imprimir.
- **Config**: Exige JWT_SECRET fuerte en modo producción.
- **Rate Limit**: Activo por defecto con Token Bucket para suavizar picos de tráfico.

---

## 🚀 Guía de Uso Rápido

### Configuración

```python
from app.crosscutting.config import get_settings

settings = get_settings()
print(settings.chunk_size)  # Validado y tipeado
```

### Logging y Tracing

```python
from app.crosscutting.logger import logger
from app.crosscutting.tracing import span

with span("proceso_critico", {"usuario": "123"}):
    # Logs heredan trace_id automáticamente
    logger.info("Iniciando proceso", extra={"dato": "valor"})
```

### Excepciones

```python
from app.crosscutting.exceptions import DatabaseError

raise DatabaseError("Fallo conexión pool", original_error=e)
# El middleware de error capturará esto y devolverá un JSON RFC7807 estándar
```
