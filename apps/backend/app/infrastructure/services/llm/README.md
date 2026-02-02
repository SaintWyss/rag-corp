# LLM Services

## 🎯 Misión
Implementar el servicio de LLM concreto (Google) y su fake determinista para tests.

**Qué SÍ hace**
- Genera respuestas con LLM real o fake.
- Soporta generación sincrónica y streaming (según implementación).
- Expone metadata útil (prompt_version, model_id).

**Qué NO hace**
- No decide retrieval ni políticas de negocio.
- No almacena respuestas ni métricas (eso se registra en capas superiores).

**Analogía (opcional)**
- Es el “hablante” del sistema: produce texto a partir de contexto.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `fake_llm.py` | Archivo Python | LLM fake determinista para tests/CI. |
| 🐍 `google_llm_service.py` | Archivo Python | LLM real vía Google GenAI. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: query + contexto (o chunks para streaming).
- **Proceso**: provider real o fake genera texto.
- **Output**: string de respuesta o stream de tokens.

Tecnologías/librerías usadas aquí:
- google-genai (real), implementación fake local.

Flujo típico:
- Use case llama `LLMService.generate_answer()`.
- En modo streaming, se usa `generate_stream()`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (LLM).
- Recibe órdenes de: Application (use cases) y streaming.
- Llama a: proveedor externo (Google) o fake local.
- Contratos y límites: respeta `LLMService` del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.services.llm.fake_llm import FakeLLMService

llm = FakeLLMService()
answer = llm.generate_answer("hola", context="contexto")
```

## 🧩 Cómo extender sin romper nada
- Implementa un nuevo provider respetando `LLMService`.
- Agrega propiedades útiles (model_id/prompt_version) para observabilidad.
- Exporta el nuevo provider en `services/__init__.py`.

## 🆘 Troubleshooting
- Síntoma: `LLMError` por query vacía → Causa probable: input vacío → Validar en use case.
- Síntoma: proveedor real falla → Causa probable: API key/SDK → Revisar `.env` y `google_llm_service.py`.

## 🔎 Ver también
- [Services](../README.md)
- [Domain services](../../../domain/services.py)
