# llm
Como un **intérprete especializado**: toma pregunta + contexto y produce respuestas (o streaming) usando proveedores LLM concretos.

## 🎯 Misión
Este submódulo implementa **adaptadores LLM** concretos para el puerto `LLMService` del dominio. Aquí viven las implementaciones reales (Google Gemini) y el fake determinista para tests/CI, con políticas explícitas como “context-only”.

Sirve como hoja técnica: explica qué proveedores existen, cómo construyen prompts/versiones y cómo se comportan ante errores/streaming.

### Qué SÍ hace
- Implementa `LLMService` con `GoogleLLMService` (Gemini) y `FakeLLMService` (determinista).
- Usa `PromptLoader` versionado para formar el prompt final (`context` + `query`).
- Aplica política “context-only” para evitar alucinaciones si el contexto está vacío.
- Soporta streaming (`generate_stream`) con chunks de salida controlados.

### Qué NO hace (y por qué)
- No implementa embeddings ni caching. Razón: esos adapters viven en `../` (servicios de embeddings). Consecuencia: cambios de embeddings se hacen en `app/infrastructure/services/README.md`, no aquí.
- No decide qué provider usar en runtime. Razón: la selección pertenece al composition root. Consecuencia: el wiring se configura en `app/container.py`.
- No expone HTTP ni DTOs. Razón: el transporte es responsabilidad de _Interfaces_. Consecuencia: los routers llaman use cases; los use cases llaman a este puerto.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del submódulo LLM. |
| `fake_llm.py` | Archivo Python | `FakeLLMService`: respuestas y streaming deterministas para tests/CI. |
| `google_llm_service.py` | Archivo Python | `GoogleLLMService`: adapter Gemini con prompts versionados y retry. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output en el flujo LLM.

- **Input:** `query` + `context` (sync) o `query` + `chunks` (streaming).
- **Proceso:** `GoogleLLMService` arma el prompt con `PromptLoader`, aplica “context-only”, y llama al SDK de Gemini con retry (solo en el arranque de streaming).
- **Proceso:** `FakeLLMService` normaliza entradas, genera una respuesta hash determinista y emite chunks de tamaño fijo.
- **Output:** `str` o `AsyncGenerator[str, None]`, y errores tipados `LLMError` si faltan inputs o credenciales.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** _Infrastructure_ (adapter a proveedor LLM).
- **Recibe órdenes de:** casos de uso de `app/application/` que generan respuestas RAG.
- **Llama a:** `google.genai.Client`, `app/infrastructure/prompts/PromptLoader`, `app/infrastructure/services/retry.py`, `app/application/context_builder` (lazy import).
- **Reglas de límites:** no importar routers/DTOs; no decidir reglas de negocio.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: uso recomendado vía composition root (wiring centralizado).
from app.container import get_llm_service

llm = get_llm_service()
answer = llm.generate_answer(query="Q", context="CTX")
```

```python
# Por qué: inyectar client ayuda a testear sin tocar env vars.
from google import genai
from app.infrastructure.services.llm.google_llm_service import GoogleLLMService

client = genai.Client(api_key="dummy")
service = GoogleLLMService(client=client, model_id="gemini-1.5-flash")
```

```python
# Por qué: fake determinista para tests y CI sin red.
from app.infrastructure.services.llm.fake_llm import FakeLLMService

fake = FakeLLMService(stream_chunk_size=8)
```

## 🧩 Cómo extender sin romper nada
- Crear un nuevo provider en `app/infrastructure/services/llm/` que implemente `LLMService`.
- Mantener política “context-only” y errores tipados (`LLMError`).
- Cablear el provider en `app/container.py` (selección por settings/flags).
- Tests: unit en `apps/backend/tests/unit/` para contrato y errores; integration en `apps/backend/tests/integration/` si toca IO real.

## 🆘 Troubleshooting
- **Síntoma:** `LLMError: GOOGLE_API_KEY not configured`.
- **Causa probable:** no se inyectó `api_key` ni existe `GOOGLE_API_KEY`.
- **Dónde mirar:** `google_llm_service.py` y `.env`.
- **Solución:** definir `GOOGLE_API_KEY` o inyectar `client` en tests.
- **Síntoma:** respuesta vacía cuando no hay contexto.
- **Causa probable:** política “context-only” activa.
- **Dónde mirar:** `GoogleLLMService._context_only_fallback()`.
- **Solución:** asegurar contexto no vacío o ajustar policy a nivel de aplicación.
- **Síntoma:** streaming corta a mitad.
- **Causa probable:** error durante el stream (no reintenta por idempotencia).
- **Dónde mirar:** `generate_stream` en `google_llm_service.py`.
- **Solución:** revisar logs y reintentar a nivel de cliente.
- **Síntoma:** tests flaky con streaming.
- **Causa probable:** chunk size distinto al esperado.
- **Dónde mirar:** `FakeLLMService(stream_chunk_size=...)`.
- **Solución:** fijar tamaño en tests o adaptar asserts.

## 🔎 Ver también
- `../README.md`
- `../../prompts/README.md`
- `../../application/usecases/chat/README.md`
- `../../crosscutting/exceptions.py`
