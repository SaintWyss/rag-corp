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

- No carga ni formatea prompts.
  - **Razón:** la lectura, validación y cache pertenecen a _Infrastructure_ (`infrastructure/prompts/loader.py`).
  - **Impacto:** editar un `.md` no tiene efecto hasta que el proceso recarga el loader (ver Troubleshooting).

- No contiene código ejecutable.
  - **Razón:** es un paquete de assets estáticos.
  - **Impacto:** los cambios se prueban invocando el loader desde el runtime/tests, no “corriendo” este módulo.

## 🗺️ Mapa del territorio

| Recurso       | Tipo      | Responsabilidad (en humano)                                             |
| :------------ | :-------- | :---------------------------------------------------------------------- |
| `policy/`     | Carpeta   | Contrato global de seguridad del LLM (se antepone al resto de prompts). |
| `rag_answer/` | Carpeta   | Prompts de respuesta RAG versionados por archivo (v1, v2, …).           |
| `README.md`   | Documento | Portada + índice de navegación del módulo de prompts.                   |

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

### 1) Cargar el prompt configurado por settings (patrón del proyecto)

```python
from app.infrastructure.prompts.loader import get_prompt_loader

loader = get_prompt_loader()  # usa settings.prompt_version
prompt = loader.format(context="...", query="...")
```

### 2) Forzar versión/capability en un test

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v2", capability="rag_answer", lang="es")
prompt = loader.format(context="CTX", query="Q")
assert "CTX" in prompt
assert "Q" in prompt
```

### 3) Estructura mínima de un template con frontmatter

```text
---
type: rag_answer
version: "1.1"
lang: es
inputs:
  - context
  - query
---

# Título

Usá este contexto:
{context}

Pregunta:
{query}
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo cambio grande → nueva versión**:
   - agregá `v3_es.md` en `rag_answer/` (no edites una versión estable si ya está en uso).

2. **Respetá naming**:
   - `rag_answer/{version}_{lang}.md` (ej. `v2_es.md`).

3. **Respetá tokens obligatorios**:
   - `{context}` y `{query}` deben existir en el cuerpo del prompt.

4. **Mantené frontmatter consistente**:
   - declarás `inputs` y alineás con lo que el loader reemplaza.

5. **Cableado / activación**:
   - cambiá `settings.prompt_version` (config) para apuntar a la nueva versión.

6. **Tests recomendados**:
   - un test simple que instancie `PromptLoader(version=...)` y valide que formatea sin errores.

## 🆘 Troubleshooting

- **`ValueError: Invalid prompt version`** → la versión no cumple `vN` → usar `v1`, `v2`, `v3`, … en `settings.prompt_version`.
- **Se pide `v2` pero termina usando `v1`** → falta `rag_answer/v2_es.md` → crear el archivo con ese nombre exacto.
- **`ValueError: Prompt template missing required tokens`** → el template no tiene `{context}` o `{query}` → agregarlos en el cuerpo.
- **El prompt “no cambia” después de editar un `.md`** → loader cacheado (`get_prompt_loader()` usa cache) → reiniciar el proceso o crear un `PromptLoader(...)` nuevo en tests.
- **Tokens quedan sin reemplazar** → se está enviando el template crudo y no el resultado de `format(...)` → revisar el punto donde se construye el prompt final.

## 🔎 Ver también

- `../infrastructure/prompts/README.md` (loader, cache, validación, fallback)
- `./policy/README.md` (contrato de seguridad global)
- `./rag_answer/README.md` (prompts versionados de respuesta RAG)
