# RAG Answer Prompts

## 🎯 Misión
Definir prompts versionados para generar respuestas RAG con citas y formato consistente.

**Qué SÍ hace**
- Provee versiones de prompt (v1, v2) con reglas y formato.
- Declara inputs requeridos (`context`, `query`) en frontmatter.

**Qué NO hace**
- No ejecuta lógica de aplicación.
- No decide qué versión usar (eso se configura en settings).

**Analogía (opcional)**
- Es el “guion” que guía la respuesta del asistente.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📄 `README.md` | Documento | Esta documentación. |
| 📄 `v1_es.md` | Documento | Prompt base en español (versionado). |
| 📄 `v2_es.md` | Documento | Prompt avanzado con formato y confianza. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `context` y `query` desde el caso de uso RAG.
- **Proceso**: `PromptLoader` selecciona la versión y reemplaza tokens.
- **Output**: prompt final para el LLM.

Tecnologías/librerías usadas aquí:
- Markdown con frontmatter YAML.

## 🔗 Conexiones y roles
- Rol arquitectónico: Static Assets / Configuration.
- Recibe órdenes de: `PromptLoader` y servicios LLM.
- Llama a: no aplica.
- Contratos y límites: debe incluir `{context}` y `{query}`.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v2", capability="rag_answer")
prompt = loader.format(context="...", query="...")
```

## 🧩 Cómo extender sin romper nada
- Crea una nueva versión `v3_es.md` si cambias formato o reglas.
- Mantén `inputs` en frontmatter alineados con tokens.
- Prueba manualmente que el prompt respeta la policy.

## 🆘 Troubleshooting
- Síntoma: prompt version no encontrada → Causa probable: `prompt_version` inválida → Revisar `config.py`.
- Síntoma: `{context}` aparece sin reemplazar → Causa probable: token faltante → Revisar frontmatter.

## 🔎 Ver también
- [Policy prompts](../policy/README.md)
- [Prompt Loader](../../infrastructure/prompts/README.md)
