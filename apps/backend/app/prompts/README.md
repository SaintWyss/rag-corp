# prompts
Como un **repositorio de guiones**: guarda prompts versionados para que el loader los combine y se los pase al LLM.

## 🎯 Misión

Este módulo contiene los **templates de prompts** (Markdown) que alimentan al LLM. Están separados del código Python para poder versionarlos y revisarlos como “assets” del producto.

Recorridos rápidos por intención:

- **Quiero entender cómo se cargan y formatean** → `../infrastructure/prompts/README.md`
- **Quiero tocar el contrato global de seguridad** → `./policy/README.md` (y `secure_contract_es.md`)
- **Quiero ajustar el prompt de respuesta RAG** → `./rag_answer/README.md` (y archivos `v*_es.md`)

### Qué SÍ hace

- Organiza prompts por **capacidad** (ej. `policy`, `rag_answer`).
- Mantiene **versiones** por archivo (ej. `v1_es.md`, `v2_es.md`).
- Define metadata en **frontmatter YAML** (tipo, versión, idioma, inputs) para validación.

### Qué NO hace (y por qué)

- No carga ni formatea prompts. Razón: ** la lectura, validación y cache pertenecen a _Infrastructure_ (`infrastructure/prompts/loader.py`). Impacto: ** editar un `.md` no tiene efecto hasta que el proceso recarga el loader (ver Troubleshooting).

- No contiene código ejecutable. Razón: ** es un paquete de assets estáticos. Impacto: ** los cambios se prueban invocando el loader desde el runtime/tests, no “corriendo” este módulo.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :------------ | :-------- | :---------------------------------------------------------------------- |
| `policy` | Carpeta | Contrato global de seguridad del LLM (se antepone al resto de prompts). |
| `rag_answer` | Carpeta | Prompts de respuesta RAG versionados por archivo (v1, v2, …). |
| `README.md` | Documento | Portada + índice de navegación del módulo de prompts. |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output (flujo real del loader).

- **Input:** configuración runtime del loader:
- `settings.prompt_version` (ej. `"v1"`, `"v2"`).
- `capability` (por defecto `rag_answer`).
- `lang` (por defecto `es`).

- **Proceso:** `PromptLoader` (infraestructura) hace lo siguiente:
  1. Resuelve rutas seguras dentro de `app/prompts/`.
  2. Carga **policy** desde `policy/secure_contract_es.md`.
  3. Carga el template de la capability: `rag_answer/{version}_{lang}.md`.
- Si el archivo no existe y la versión pedida no es `v1`, hace **fallback a `v1`**.

  4. Parseo de frontmatter YAML y validación mínima.
  5. Compone el prompt final como `policy + template`.
  6. En `format(context, query)`, reemplaza **solo** `{context}` y `{query}`.
- Si faltan tokens en el template, lanza `ValueError`.

- **Output:** un string listo para enviar al LLM.

Conceptos en contexto:

- **Frontmatter YAML:** bloque entre `---` que declara metadata e `inputs`.
- **Tokens `{context}` / `{query}`:** placeholders obligatorios para el loader.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Static Assets / Configuration.

- **Recibe órdenes de:**
- `PromptLoader` en `app/infrastructure/prompts/loader.py`.

- **Llama a:** no aplica.

- **Reglas de límites (ownership):**
- Este módulo no decide versiones ni formato final.
- Los templates deben respetar:
- naming: `{version}_{lang}.md` (ej. `v2_es.md`).
- tokens: `{context}` y `{query}` presentes.
- frontmatter coherente (`type`, `version`, `lang`, `inputs`).

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v2", capability="rag_answer", lang="es")
prompt = loader.format(context="CTX", query="Q")
```

```text
---
type: rag_answer
version: "2.0"
lang: es
inputs:
  - context
  - query
---

Contexto:
{context}

Pregunta:
{query}
```

## 🧩 Cómo extender sin romper nada
- Para cambios grandes, crear nueva versión `vN`.
- Mantener `{context}` y `{query}` en el template.
- Actualizar `settings.prompt_version` para activar la nueva versión.
- Si el consumo cambia, cablear el loader desde `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/` con `PromptLoader`.

## 🆘 Troubleshooting
- **Síntoma:** versión no encontrada.
- **Causa probable:** falta `vN_es.md`.
- **Dónde mirar:** `rag_answer/`.
- **Solución:** crear el archivo con nombre exacto.
- **Síntoma:** tokens sin reemplazar.
- **Causa probable:** se usa template crudo.
- **Dónde mirar:** punto donde se llama `format()`.
- **Solución:** usar `PromptLoader.format(...)`.
- **Síntoma:** cambios no se reflejan.
- **Causa probable:** loader cacheado.
- **Dónde mirar:** `get_prompt_loader()`.
- **Solución:** reiniciar proceso.

## 🔎 Ver también
- `../infrastructure/prompts/README.md`
- `./policy/README.md`
- `./rag_answer/README.md`
