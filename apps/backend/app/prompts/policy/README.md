# policy
Como un **reglamento interno**: define reglas globales de seguridad y evidencia que se anteponen a cualquier prompt.

## 🎯 Misión

Este directorio contiene el **contrato de seguridad global** del sistema. Se concatena automáticamente antes de cualquier template de tarea (por ejemplo, `rag_answer`) para imponer límites no negociables: seguridad, uso de evidencia y comportamiento ante falta de información.

Recorridos rápidos por intención:

- **Quiero ver cómo se carga y se concatena policy** → `../../infrastructure/prompts/README.md`
- **Quiero ajustar el prompt de respuesta RAG** → `../rag_answer/README.md`
- **Quiero el índice general de prompts** → `../README.md`

### Qué SÍ hace

- Define reglas globales no negociables (seguridad, evidencia, manejo de incertidumbre).
- Se incluye automáticamente antes del template versionado de la capability.
- Establece contratos de formato que afectan a todo el sistema (por ejemplo, cómo citar fuentes).

### Qué NO hace (y por qué)

- No contiene lógica de ejecución. Razón: ** es un asset estático; la aplicación ejecuta reglas en código y el loader solo compone texto. Impacto: ** cambios acá se reflejan al construir el prompt final (no hay “código” que correr).

- No define prompts específicos de tarea. Razón: ** las tareas viven en directorios por capability (ej. `rag_answer/`). Impacto: ** si querés cambiar estructura de respuesta, se hace en el prompt de la capability, no acá.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :---------------------- | :-------- | :-------------------------------------------------------------------- |
| `README.md` | Documento | Portada + reglas de extensión del contrato global. |
| `secure_contract_es.md` | Documento | Contrato de seguridad en español que se antepone a todos los prompts. |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output (flujo real del loader).

- **Input:** `PromptLoader` (infra) carga policy + template por capability.
- **Proceso:**
  1. Lee `policy/secure_contract_es.md`.
  2. Lee el prompt de la capability (ej. `rag_answer/v2_es.md`).
  3. Concatena `policy + template` en un único string.
  4. En `format(...)`, reemplaza tokens del template (ej. `{context}`, `{query}`) y devuelve el prompt final.

- **Output:** prompt final con reglas globales aplicadas.

Conceptos en contexto:

- **Policy** no es “un prompt más”: es la base que define límites globales.
- **Fuentes `[S#]`**: si el sistema usa un formato de fuentes específico, la policy debe estar alineada con ese contrato para evitar salidas inconsistentes.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Static Assets / Configuration.

- **Recibe órdenes de:**
- `PromptLoader` en infraestructura.

- **Llama a:** no aplica.

- **Reglas de límites (contratos):**
- Debe ser consistente con el formato de citación esperado (`[S#]` u otro) para que el consumidor no tenga que “adivinar”.
- Debe evitar contradicciones internas (reglas que se anulan entre sí).
- Debe mantenerse estable: cambios impactan a todas las capabilities.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer", lang="es")
policy_plus_template = loader.get_template()
```

```text
# Checklist manual
- No contradice reglas del sistema
- No introduce tokens no reemplazables
```

## 🧩 Cómo extender sin romper nada
- Mantener policy breve y global (no específica de una sola tarea).
- Evitar tokens que el loader no reemplaza.
- Si el cambio es breaking, versionar la capability y documentar.
- Si el consumo cambia, cablear el loader desde `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/` con `PromptLoader.format(...)`.

## 🆘 Troubleshooting
- **Síntoma:** respuestas sin fuentes.
- **Causa probable:** policy y template desalineados.
- **Dónde mirar:** `secure_contract_es.md` y `rag_answer/`.
- **Solución:** alinear reglas y formato.
- **Síntoma:** `FileNotFoundError` de policy.
- **Causa probable:** archivo faltante o renombrado.
- **Dónde mirar:** `infrastructure/prompts/loader.py`.
- **Solución:** restaurar `secure_contract_es.md`.
- **Síntoma:** tokens literales en salida.
- **Causa probable:** policy agregó placeholders no soportados.
- **Dónde mirar:** policy.
- **Solución:** eliminar tokens no soportados.
- **Síntoma:** cambios no se reflejan.
- **Causa probable:** loader cacheado.
- **Dónde mirar:** `get_prompt_loader()`.
- **Solución:** reiniciar proceso.

## 🔎 Ver también
- `../README.md`
- `../rag_answer/README.md`
- `../../infrastructure/prompts/README.md`
