# Infra: External Services (AI/ML)

## 🎯 Misión

Adapta servicios externos (especialmente de Inteligencia Artificial) para que sean consumibles por el dominio.
Maneja la complejidad de llamar a APIs de terceros, reintentos (retries) y mocks para pruebas.

**Qué SÍ hace:**

- Clientes para Embeddings (Google, OpenAI, Fake).
- Estrategias de Caché y Retry.
- Clientes LLM (ver subcarpeta `llm/`).

**Qué NO hace:**

- No decide qué prompt enviar (eso es `application`).

## 🗺️ Mapa del territorio

| Recurso                       | Tipo       | Responsabilidad (en humano)                                              |
| :---------------------------- | :--------- | :----------------------------------------------------------------------- |
| `llm/`                        | 📁 Carpeta | Implementaciones de Modelos de Lenguaje (LLM).                           |
| `cached_embedding_service.py` | 🐍 Archivo | Decorador que cachea vectores para no gastar dinero repitiendo cálculos. |
| `fake_embedding_service.py`   | 🐍 Archivo | Mock determinista para tests (devuelve vectores fijos).                  |
| `google_embedding_service.py` | 🐍 Archivo | Cliente para Google Vertex AI / Gemini Embeddings.                       |
| `retry.py`                    | 🐍 Archivo | Utilidad genérica para reintentar llamadas con backoff exponencial.      |

## ⚙️ ¿Cómo funciona por dentro?

Todas implementan el protocolo `EmbeddingService` definido en el Dominio.
El `CachedEmbeddingService` es un **Proxy** que envuelve al servicio real y consulta Redis antes de llamar a la API externa.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapters (External APIs).
- **Llama a:** APIs HTTP externas.

## 👩‍💻 Guía de uso (Snippets)

### Usar Embbedings

```python
service = GoogleEmbeddingService(api_key="...")
vector = service.embed_text("Hola mundo")
# vector es list[float]
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevo Proveedor:** Crea `openai_embedding_service.py` e implementa la interfaz.
2.  **Registro:** No olvides registrarlo en `app/container.py` basado en la configuración.

## 🔎 Ver también

- [Servicios LLM](./llm/README.md)
