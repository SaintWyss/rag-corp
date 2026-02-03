# rag_answer

Como un **guion de respuesta**: define el formato y las reglas con las que el asistente arma respuestas RAG con citas.

## 🎯 Misión

Este directorio contiene los **prompts versionados** para generar respuestas RAG con formato consistente (estructura, tono y reglas de citación). Se cargan como assets y se combinan con la policy global antes de enviarse al LLM.

Recorridos rápidos por intención:

- **Quiero entender cómo se selecciona versión/idioma y cómo se formatea** → `../../infrastructure/prompts/README.md`
- **Quiero tocar el contrato global de seguridad** → `../policy/README.md`
- **Quiero cambiar el formato de respuesta RAG** → editar/crear `v*_es.md` en este mismo directorio

### Qué SÍ hace

- Provee prompts **versionados** (ej. `v1_es.md`, `v2_es.md`) para la capability `rag_answer`.
- Declara `inputs` requeridos en frontmatter YAML (mínimo: `context`, `query`).
- Mantiene reglas de salida: estructura, citas y manejo de incertidumbre según cada versión.

### Qué NO hace (y por qué)

- No ejecuta lógica de aplicación.
  - **Razón:** es un asset estático; la orquestación vive en Application y el loader en Infrastructure.
  - **Impacto:** los cambios se prueban vía `PromptLoader.format(...)`, no “corriendo” este módulo.

- No decide qué versión usar.
  - **Razón:** la elección es configuración (`settings.prompt_version`).
  - **Impacto:** si falta el archivo de la versión, el loader puede hacer fallback (según implementación).

## 🗺️ Mapa del territorio

| Recurso     | Tipo      | Responsabilidad (en humano)                                                |
| :---------- | :-------- | :------------------------------------------------------------------------- |
| `README.md` | Documento | Portada + índice de prompts `rag_answer` y reglas de extensión.            |
| `v1_es.md`  | Documento | Prompt base en español: estructura mínima, citas y reglas centrales.       |
| `v2_es.md`  | Documento | Prompt avanzado: formato más estricto y directrices de confianza/claridad. |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output (flujo real del loader).

- **Input:**
  - `context`: contexto RAG ya construido (chunks, citas, metadata relevante).
  - `query`: pregunta del usuario (posiblemente reescrita por el pipeline).

- **Proceso:**
  1. `PromptLoader` carga el contrato global `policy`.
  2. Selecciona el archivo `rag_answer/{version}_{lang}.md`.
  3. Parseo del frontmatter YAML y validación mínima.
  4. Compone `policy + rag_answer_template`.
  5. Reemplaza tokens: `{context}` y `{query}` (solo esos).

- **Output:** string final que se envía al LLM.

Conceptos en contexto:

- **Context:** no es “cualquier texto”; es el material que el sistema considera evidencia para responder.
- **Citas:** el prompt define cómo el asistente referencia el contexto (formato y ubicación).

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Static Assets / Configuration.

- **Recibe órdenes de:**
  - `PromptLoader` (infraestructura) y el servicio LLM que finalmente envía el prompt.

- **Llama a:** no aplica.

- **Reglas de límites (contratos):**
  - Cada versión debe incluir `{context}` y `{query}` en el cuerpo.
  - El frontmatter debe declarar `inputs: [context, query]`.
  - Naming esperado: `vN_{lang}.md` (ej. `v3_es.md`).

## 👩‍💻 Guía de uso (Snippets)

### 1) Cargar una versión específica

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v2", capability="rag_answer", lang="es")
prompt = loader.format(context="...", query="...")
```

### 2) Test rápido de sanidad (tokens reemplazables)

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer", lang="es")
prompt = loader.format(context="CTX", query="Q")
assert "CTX" in prompt
assert "Q" in prompt
```

### 3) Esqueleto mínimo de un prompt (frontmatter + tokens)

```text
---
type: rag_answer
version: "2.0"
lang: es
inputs:
  - context
  - query
---

Instrucciones:
- Respondé usando solo el contexto.
- Citá fragmentos cuando corresponda.

Contexto:
{context}

Pregunta:
{query}
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Cambio grande → nueva versión**: creá `v3_es.md` (no rompas una versión estable si ya está en uso).
2. **Respetá naming**: `vN_es.md` para español (alineado a `settings.prompt_version`).
3. **Respetá tokens**: `{context}` y `{query}` deben estar en el cuerpo.
4. **Frontmatter coherente**: `type`, `version`, `lang` e `inputs` alineados con lo que el loader reemplaza.
5. **Compatibilidad**: si cambiás formato de citas/estructura, verificá que el consumidor (post-processing) no dependa del layout anterior.
6. **Validación manual**: probá con 2 contextos:
   - uno con evidencia clara (debería citar y responder directo).
   - uno incompleto (debería declarar incertidumbre y pedir dato faltante).

## 🆘 Troubleshooting

- **No existe la versión pedida** → falta `vN_es.md` con el nombre exacto → crear el archivo o corregir `settings.prompt_version`.
- **`{context}` o `{query}` quedan sin reemplazar** → se está usando el template crudo o el token no está presente → revisar que se llame a `format(...)` y que el cuerpo contenga los tokens.
- **Error por “missing required tokens”** → el template no incluye ambos tokens → agregarlos en el cuerpo.
- **El prompt no refleja cambios** → loader cacheado en runtime → reiniciar proceso o invalidar cache (según implementación del loader).

## 🔎 Ver también

- `../policy/README.md` (contrato global de seguridad)
- `../../infrastructure/prompts/README.md` (selección, cache, validación y formato)
- `../README.md` (índice de p
