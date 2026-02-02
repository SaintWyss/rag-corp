# Prompts (templates)

## 🎯 Misión
Almacenar los templates de prompts versionados que alimentan al LLM, separados del código Python.

**Qué SÍ hace**
- Organiza prompts por capacidad (`policy`, `rag_answer`).
- Mantiene versiones (`v1`, `v2`, ...).
- Usa frontmatter para metadata e inputs.

**Qué NO hace**
- No carga ni formatea prompts (eso está en `infrastructure/prompts`).
- No contiene código ejecutable.

**Analogía (opcional)**
- Es el “repositorio de guiones” que el LLM sigue.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📁 `policy/` | Carpeta | Contratos de seguridad globales del LLM. |
| 📁 `rag_answer/` | Carpeta | Prompts de respuesta RAG por versión. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: versión configurada (ej. `prompt_version=v1`).
- **Proceso**: `PromptLoader` combina policy + prompt y reemplaza `{context}`/`{query}`.
- **Output**: prompt final enviado al LLM.

Tecnologías/librerías usadas aquí:
- Markdown con frontmatter YAML.

Flujo típico:
- `infrastructure/prompts/loader.py` lee `policy/` y `rag_answer/`.
- La app llama `PromptLoader.format()` con context/query.

## 🔗 Conexiones y roles
- Rol arquitectónico: Static Assets / Configuration.
- Recibe órdenes de: `PromptLoader` en infraestructura.
- Llama a: no aplica.
- Contratos y límites: mantiene tokens `{context}` y `{query}` declarados en frontmatter.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer")
prompt = loader.format(context="...", query="...")
```

## 🧩 Cómo extender sin romper nada
- Versiona cambios grandes (`v2`, `v3`, ...).
- Mantén frontmatter con `inputs` correctos.
- No elimines `{context}`/`{query}` si el loader los espera.

## 🆘 Troubleshooting
- Síntoma: prompt no cambia al editar → Causa probable: cache en loader → Reiniciar proceso.
- Síntoma: tokens sin reemplazar → Causa probable: inputs no declarados → Revisar frontmatter.

## 🔎 Ver también
- [Prompt Loader](../infrastructure/prompts/README.md)
- [Policy](./policy/README.md)
- [RAG Answer](./rag_answer/README.md)
