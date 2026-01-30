"""
Infrastructure Services (Infrastructure Layer)

Qué es este módulo
------------------
Este archivo actúa como **Facade/Barrel** del paquete `infrastructure.services`.
Su única función es **exponer una API pública estable** (re-exportar símbolos)
para que el resto del sistema (composición/DI, aplicación) importe desde un único lugar,
sin acoplarse a la estructura interna de carpetas.

Arquitectura
------------
- Estilo: **Clean Architecture / Hexagonal**
- Capa: **Infrastructure**
- Rol: Implementar **adapters** concretos (Google, cache, retry) de interfaces del dominio.

Patrones de diseño presentes (a nivel paquete)
----------------------------------------------
- **Facade / Barrel (Package Facade):** este `__init__.py` agrupa exports.
- **Adapter:** `GoogleEmbeddingService`, `GoogleLLMService` adaptan SDK externo a interfaces del dominio.
- **Decorator:** `CachingEmbeddingService` agrega caching a un `EmbeddingService`.
- **Test Double / Fake:** `FakeEmbeddingService`, `FakeLLMService` para tests/desarrollo.
- **Retry / Resilience (Decorator):** utilidades de `retry` envuelven funciones con reintentos.

SOLID (impacto/justificación)
-----------------------------
- **SRP:** este módulo *solo* define la API pública del paquete (sin lógica de negocio).
- **OCP:** podés agregar nuevas implementaciones/adapters sin romper import paths (solo sumar exports).
- **LSP:** fakes pueden reemplazar implementaciones reales (si respetan las interfaces del dominio).
- **ISP:** las capas superiores dependen de interfaces del dominio, no de SDKs concretos.
- **DIP:** dominio/app dependen de abstracciones; infraestructura aporta implementaciones.

CRC (Component Card)
--------------------
Component: infrastructure.services (Facade)
Responsibilities:
  - Publicar un “surface area” estable del paquete (imports canónicos)
  - Evitar que consumidores dependan de rutas internas (reduce acoplamiento)
  - Centralizar exports para DX y mantenibilidad
Collaborators:
  - composition root / container (inyecta dependencias)
  - application layer (consume servicios vía interfaces)
Constraints:
  - No contener lógica (solo re-export y documentación)
  - Imports ordenados por dominios funcionales (embeddings/llm/resilience)
"""

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
from .cached_embedding_service import CachingEmbeddingService  # noqa: F401
from .fake_embedding_service import FakeEmbeddingService  # noqa: F401
from .google_embedding_service import GoogleEmbeddingService  # noqa: F401

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
from .llm.fake_llm import FakeLLMService  # noqa: F401
from .llm.google_llm_service import GoogleLLMService  # noqa: F401

# ---------------------------------------------------------------------------
# Resilience / Retry utilities
# (Notas: estas utilidades suelen pertenecer a "crosscutting/resilience",
#  pero se exportan acá para conveniencia del paquete.)
# ---------------------------------------------------------------------------
from .retry import (  # noqa: F401
    PERMANENT_HTTP_CODES,
    TRANSIENT_HTTP_CODES,
    create_retry_decorator,
    is_transient_error,
    with_retry,
)

# API pública del paquete (lo que los consumidores deberían importar)
__all__ = [
    # Embeddings
    "CachingEmbeddingService",
    "FakeEmbeddingService",
    "GoogleEmbeddingService",
    # LLM
    "FakeLLMService",
    "GoogleLLMService",
    # Resilience / Retry
    "is_transient_error",
    "create_retry_decorator",
    "with_retry",
    "TRANSIENT_HTTP_CODES",
    "PERMANENT_HTTP_CODES",
]
