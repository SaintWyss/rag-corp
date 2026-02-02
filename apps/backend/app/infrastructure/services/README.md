# Infrastructure Services

## 🎯 Misión
Proveer implementaciones concretas de servicios externos (embeddings, LLM) y utilidades de resiliencia (retry), encapsulando SDKs y detalles técnicos.

**Qué SÍ hace**
- Implementa servicios de embeddings (Google, fake) y caching.
- Implementa servicios LLM (Google, fake).
- Provee utilidades de reintentos para llamadas externas.

**Qué NO hace**
- No contiene reglas de negocio.
- No expone endpoints ni DTOs HTTP.

**Analogía (opcional)**
- Es el “puente” hacia proveedores externos.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Facade de exports de servicios. |
| 🐍 `cached_embedding_service.py` | Archivo Python | Decorator de cache para embeddings. |
| 🐍 `fake_embedding_service.py` | Archivo Python | Embeddings fake para tests/dev. |
| 🐍 `google_embedding_service.py` | Archivo Python | Embeddings reales via Google GenAI. |
| 📁 `llm/` | Carpeta | Implementaciones de LLM (fake/Google). |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `retry.py` | Archivo Python | Utilidades de retry (transient/permanent). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: textos (embeddings) o prompts (LLM) desde casos de uso.
- **Proceso**: llamadas a SDKs externos o fakes locales; retry opcional.
- **Output**: embeddings o texto generado.

Tecnologías/librerías usadas aquí:
- google-genai, tenacity (retry), numpy (embeddings), fakes locales.

Flujo típico:
- `CachingEmbeddingService` envuelve un proveedor real/fake.
- `GoogleLLMService` genera texto y expone stream si aplica.
- `retry.py` define qué errores son transitorios.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (servicios externos).
- Recibe órdenes de: Application (use cases) vía puertos del dominio.
- Llama a: proveedores externos (Google) o fakes internos.
- Contratos y límites: respeta `EmbeddingService` y `LLMService` del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.services import CachingEmbeddingService, FakeEmbeddingService
from app.infrastructure.cache import get_embedding_cache

service = CachingEmbeddingService(
    provider=FakeEmbeddingService(),
    cache=get_embedding_cache(),
)
```

## 🧩 Cómo extender sin romper nada
- Implementa un nuevo proveedor respetando `EmbeddingService` o `LLMService`.
- Expórtalo desde `services/__init__.py`.
- Usa `retry.py` si el SDK es inestable.
- Agrega tests unitarios para el adapter.

## 🆘 Troubleshooting
- Síntoma: llamadas externas fallan → Causa probable: API key inválida → Mirar `.env` y `config.py`.
- Síntoma: embeddings vacíos → Causa probable: input vacío o proveedor fake → Mirar `FakeEmbeddingService`.
- Síntoma: errores intermitentes → Causa probable: red → Revisa `retry.py`.

## 🔎 Ver también
- [LLM services](./llm/README.md)
- [Embedding cache](../cache.py)
- [Domain services](../../domain/services.py)
