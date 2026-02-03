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

- No ejecuta lógica de aplicación. Razón: ** es un asset estático; la orquestación vive en Application y el loader en Infrastructure. Impacto: ** los cambios se prueban vía `PromptLoader.format(...)`, no “corriendo” este módulo.

- No decide qué versión usar. Razón: ** la elección es configuración (`settings.prompt_version`). Impacto: ** si falta el archivo de la versión, el loader puede hacer fallback (según implementación).

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :---------- | :-------- | :------------------------------------------------------------------------- |
| `README.md` | Documento | Portada + índice de prompts `rag_answer` y reglas de extensión. |
| `v1_es.md` | Documento | Prompt base en español: estructura mínima, citas y reglas centrales. |
| `v2_es.md` | Documento | Prompt avanzado: formato más estricto y directrices de confianza/claridad. |

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
- Para cambios grandes, crear `vN_es.md` nuevo.
- Mantener `{context}` y `{query}` en el cuerpo.
- Actualizar `settings.prompt_version` para activar la versión.
- Si el consumo cambia, cablear el loader desde `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/` con `PromptLoader`.

## 🆘 Troubleshooting
- **Síntoma:** versión no encontrada.
- **Causa probable:** archivo `vN_es.md` ausente.
- **Dónde mirar:** este directorio.
- **Solución:** crear el archivo con el nombre exacto.
- **Síntoma:** tokens quedan literales.
- **Causa probable:** template sin tokens o uso incorrecto del loader.
- **Dónde mirar:** template y `PromptLoader`.
- **Solución:** agregar tokens y usar `format()`.
- **Síntoma:** cambios no se reflejan.
- **Causa probable:** loader cacheado.
- **Dónde mirar:** `get_prompt_loader()`.
- **Solución:** reiniciar proceso.
- **Síntoma:** output no respeta formato.
- **Causa probable:** template modificado sin actualizar policy.
- **Dónde mirar:** `policy/`.
- **Solución:** alinear policy y template.

## 🔎 Ver también
- `../README.md`
- `../policy/README.md`
- `../../infrastructure/prompts/README.md`
