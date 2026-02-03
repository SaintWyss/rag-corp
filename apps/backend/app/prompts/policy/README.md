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

- No contiene lógica de ejecución.
  - **Razón:** es un asset estático; la aplicación ejecuta reglas en código y el loader solo compone texto.
  - **Impacto:** cambios acá se reflejan al construir el prompt final (no hay “código” que correr).

- No define prompts específicos de tarea.
  - **Razón:** las tareas viven en directorios por capability (ej. `rag_answer/`).
  - **Impacto:** si querés cambiar estructura de respuesta, se hace en el prompt de la capability, no acá.

## 🗺️ Mapa del territorio

| Recurso                 | Tipo      | Responsabilidad (en humano)                                           |
| :---------------------- | :-------- | :-------------------------------------------------------------------- |
| `README.md`             | Documento | Portada + reglas de extensión del contrato global.                    |
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

### 1) Obtener policy + template ya concatenados

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer", lang="es")
policy_plus_template = loader.get_template()
print(policy_plus_template[:500])
```

### 2) Formatear un prompt final (incluye policy automáticamente)

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v2", capability="rag_answer", lang="es")
prompt = loader.format(context="...", query="...")
assert "..." in prompt
```

### 3) Checklist rápido de revisión de policy (manual)

```text
- No contradice reglas del sistema (seguridad / fuentes / evidencia).
- No fuerza un formato imposible para el template.
- No introduce tokens que el loader no reemplaza.
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Mantené el contrato corto y directo**: reglas globales, no detalles de una sola tarea.
2. **Evitá contradicciones**: una regla por intención; sin duplicados que divergen.
3. **No inventes tokens**: si agregás placeholders, el loader debe reemplazarlos (si no, quedarán literales).
4. **Versionado**:
   - si el cambio altera comportamiento esperado de salida (citas, evidencia, seguridad), tratá el cambio como “breaking” y documentalo.

5. **Validación**:
   - corré un sanity test que haga `PromptLoader(...).format(...)` y verifique que el prompt final incluye policy.

## 🆘 Troubleshooting

- **Respuestas sin “Fuentes”** → policy y prompt de capability desalineados → revisar `secure_contract_es.md` y el template en `../rag_answer/`.
- **El loader falla al cargar policy** → frontmatter YAML inválido o archivo malformado → revisar encabezado en `secure_contract_es.md`.
- **Aparecen literales tipo `{algo}` en la salida** → policy introdujo tokens que el loader no reemplaza → remover o implementar reemplazo en infraestructura.
- **Cambió el comportamiento de todas las respuestas** → se editó policy → revertir o documentar el cambio y ajustar prompts/tests.

## 🔎 Ver también

- `../README.md` (índice general de prompts)
- `../rag_answer/README.md` (prompts de respuesta RAG)
- `../../infrastructure/prompts/README.md` (loader, c
