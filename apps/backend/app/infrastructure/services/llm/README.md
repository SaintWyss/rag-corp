# Infra: LLM Services (Generative AI)

## 🎯 Misión

Implementaciones concretas de los Modelos de Lenguaje (Generación de texto).
Transforma prompts (strings) en respuestas (strings o streams).

**Qué SÍ hace:**

- Cliente para Google Gemini (`google_llm_service.py`).
- Cliente Mock (`fake_llm.py`) para tests sin costo.

**Qué NO hace:**

- No construye el prompt (eso es `application/context_builder.py`).

## 🗺️ Mapa del territorio

| Recurso                 | Tipo       | Responsabilidad (en humano)                                 |
| :---------------------- | :--------- | :---------------------------------------------------------- |
| `fake_llm.py`           | 🐍 Archivo | Simula un LLM repitiendo el input o devolviendo texto fijo. |
| `google_llm_service.py` | 🐍 Archivo | Adaptador para Google Generative AI (Gemini Pro).           |

## ⚙️ ¿Cómo funciona por dentro?

Implementa `LLMService` del Dominio.
Debe soportar dos modos:

1.  `generate(prompt) -> str`: Bloqueante.
2.  `generate_stream(prompt) -> Iterator[str]`: Streaming de tokens.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapter.
- **Llama a:** SDKs de proveedores (google-generativeai).

## 👩‍💻 Guía de uso (Snippets)

### Generación simple

```python
llm = GoogleLLMService(api_key="...", model="gemini-pro")
respuesta = llm.generate("¿Capital de Francia?")
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevo Modelo:** Si agregas OpenAI GPT-4, asegúrate de implementar tanto `generate` como `generate_stream`.

## 🆘 Troubleshooting

- **Síntoma:** Error 429 (Resource Exhausted).
  - **Causa:** Cuota de API excedida. El sistema de `retry.py` debería manejarlo, pero si persiste, aumenta límites.

## 🔎 Ver también

- [Servicios Base](../README.md)
