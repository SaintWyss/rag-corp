# Prompts Loader (infra)

## 🎯 Misión
Cargar y formatear prompts versionados desde `app/prompts/`, combinando policy + template y validando frontmatter.

**Qué SÍ hace**
- Lee templates por versión y capacidad (rag_answer, policy).
- Parsea frontmatter YAML y valida inputs.
- Cachea prompts en memoria por instancia.

**Qué NO hace**
- No contiene los prompts en sí (están en `app/prompts/`).
- No decide el contenido del prompt (solo lo carga y formatea).

**Analogía (opcional)**
- Es el “bibliotecario” que trae el prompt correcto del estante.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports del loader. |
| 🐍 `loader.py` | Archivo Python | Carga, cache y formateo de prompts. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: versión (v1, v2) + capacidad (rag_answer).
- **Proceso**: carga policy + template, parsea frontmatter y valida tokens.
- **Output**: string de prompt listo para el LLM.

Tecnologías/librerías usadas aquí:
- Python estándar (Path, regex), sin YAML externo.

Flujo típico:
- `PromptLoader.get_template()` compone policy + template.
- `PromptLoader.format()` reemplaza `{context}` y `{query}`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (filesystem prompts).
- Recibe órdenes de: servicios LLM / casos de uso.
- Llama a: filesystem local (`app/prompts`).
- Contratos y límites: evita path traversal y valida versión.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer")
prompt = loader.format(context="...", query="...")
```

## 🧩 Cómo extender sin romper nada
- Agrega nuevos prompts en `app/prompts/` con frontmatter.
- Usa versiones `vN` para mantener compatibilidad.
- Actualiza tests si cambias el formato de tokens.

## 🆘 Troubleshooting
- Síntoma: prompt no encontrado → Causa probable: versión inválida → Mirar `loader.py`.
- Síntoma: tokens sin reemplazar → Causa probable: frontmatter inputs no coincide → Revisar `.md`.

## 🔎 Ver también
- [Prompts (templates)](../../prompts/README.md)
- [RAG Answer prompts](../../prompts/rag_answer/README.md)
