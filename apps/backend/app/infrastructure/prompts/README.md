# prompts

Como un **bibliotecario**: trae el prompt correcto del estante, lo valida y lo deja listo para formatear.

## 🎯 Misión

Este módulo carga y formatea prompts versionados desde `app/prompts/`, combinando **policy + template** y validando el frontmatter (metadatos) para asegurar que los tokens requeridos existan y que la versión/capacidad solicitada sea válida.

El objetivo es que el resto del sistema (use cases/servicios LLM) pida “**versión + capacidad**” y reciba un string consistente, sin tener que saber rutas, nombres de archivos ni reglas de composición.

Recorridos rápidos por intención:

- **Quiero ver el loader y el contrato de carga** → `loader.py`
- **Quiero ver dónde viven los prompts** → `app/prompts/` (y sus README)
- **Quiero entender cómo se componen policy + template** → sección “¿Cómo funciona por dentro?”

### Qué SÍ hace

- Lee templates por **versión** y **capacidad** (ej. `rag_answer`, `policy`).
- Parsea frontmatter (YAML-like) y valida inputs/tokens requeridos.
- Cachea prompts en memoria por instancia para evitar I/O repetido.
- Protege rutas (evita path traversal) y valida versión/capacidad.

### Qué NO hace (y por qué)

- No contiene los prompts en sí.
  - **Razón:** los prompts son recursos versionados en `app/prompts/`.
  - **Impacto:** este módulo solo sabe “cargar y componer”; editar contenido se hace en los `.md` del directorio de prompts.

- No decide el contenido del prompt.
  - **Razón:** el contenido es parte del producto y evoluciona por versión.
  - **Impacto:** el loader no “opina”; si hay cambios de wording, son cambios en los archivos de prompts.

## 🗺️ Mapa del territorio

| Recurso       | Tipo           | Responsabilidad (en humano)                                                     |
| :------------ | :------------- | :------------------------------------------------------------------------------ |
| `__init__.py` | Archivo Python | Exporta `PromptLoader` y helpers públicos para imports estables.                |
| `loader.py`   | Archivo Python | Carga desde filesystem, cachea, valida frontmatter y compone policy + template. |
| `README.md`   | Documento      | Portada + guía operativa del loader.                                            |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output con pasos reales del módulo.

### 1) Resolución de “versión + capacidad”

- **Input:** `version` (ej. `v1`, `v2`) + `capability` (ej. `rag_answer`).
- **Proceso:**
  1. valida que `version` cumpla el patrón esperado (`vN`) y que `capability` sea un nombre permitido.
  2. resuelve rutas dentro de `app/prompts/` sin permitir `..` ni paths absolutos.
  3. determina qué archivos necesita cargar (template principal + policy asociada si aplica).

- **Output:** rutas seguras y determinísticas hacia los `.md`.

### 2) Lectura + parseo de frontmatter

- **Input:** contenido del archivo `.md`.
- **Proceso:**
  - separa frontmatter y body (template), y parsea el bloque de metadatos.
  - valida que los metadatos declaren los **inputs** requeridos (ej. `context`, `query`) y opcionales.
  - valida que el body contenga los tokens declarados (evita prompts con placeholders rotos).

- **Output:** `PromptTemplate(frontmatter, body)` (o equivalente) listo para composición.

### 3) Composición policy + template

- **Input:** plantilla de policy + plantilla de capacidad.
- **Proceso:**
  - concatena en el orden establecido (policy primero, luego template) con separadores estables.
  - preserva los tokens del template final.

- **Output:** un string de prompt “completo” listo para formatear.

### 4) Formateo (reemplazo de tokens)

- **Input:** `**kwargs` de formato (ej. `context=...`, `query=...`).
- **Proceso:**
  - valida que se proporcionen todos los tokens requeridos.
  - reemplaza placeholders `{token}` por valores.
  - opcional: recorta valores muy grandes o normaliza whitespace si el loader lo implementa.

- **Output:** prompt string listo para enviar al LLM.

Conceptos mínimos en contexto:

- **Frontmatter:** metadatos al inicio del `.md` que describen inputs, versión y compatibilidad.
- **Capability:** “familia” de prompt (qué tarea resuelve) como `rag_answer`.
- **Versión:** permite cambiar prompts sin romper compatibilidad; cada versión vive en `vN`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Infrastructure adapter (filesystem prompts).

- **Recibe órdenes de:**
  - `LLMService` o servicios de infraestructura que construyen prompts.
  - Casos de uso que piden “versión + capability” para una operación.

- **Llama a:**
  - filesystem local (lectura desde `app/prompts/`).

- **Reglas de límites (imports/ownership):**
  - No importa Domain/Application; es una utilidad de infraestructura.
  - No conoce HTTP ni repositorios.
  - Valida paths para evitar traversal.

## 👩‍💻 Guía de uso (Snippets)

### 1) Cargar y formatear un prompt RAG

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer")
prompt = loader.format(context="...", query="...")
print(prompt[:200])
```

### 2) Reutilizar la misma instancia (cache en memoria)

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v2", capability="rag_answer")

# primera vez lee de disco
p1 = loader.format(context="A", query="Q")

# siguientes llamadas reutilizan template cacheado
p2 = loader.format(context="B", query="Q")
```

### 3) Obtener el template compuesto (policy + template) sin formatear

```python
from app.infrastructure.prompts.loader import PromptLoader

loader = PromptLoader(version="v1", capability="rag_answer")
raw_template = loader.get_template()
print(raw_template)
```

### 4) Manejo de errores típico (prompt faltante / tokens)

```python
from app.infrastructure.prompts.loader import PromptLoader

try:
    loader = PromptLoader(version="v9", capability="rag_answer")
    loader.format(context="...", query="...")
except Exception as exc:
    # El módulo debe lanzar errores tipados (ver loader.py)
    raise RuntimeError(str(exc))
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo prompt/capability:** crear carpeta/archivo en `app/prompts/<capability>/` con versionado `vN`.
2. **Frontmatter:** declarar inputs requeridos y mantener tokens del body consistentes.
3. **Compatibilidad:** cuando cambies estructura o wording fuerte, subí versión (`v2`, `v3`) en vez de editar `v1`.
4. **Policy:** si una capability requiere policy, mantener el punto de composición estable (policy primero).
5. **Tests:**
   - unit: cargar un prompt real y validar que `format()` reemplaza tokens.
   - negativa: versión inexistente, capability inválida, token faltante.

## 🆘 Troubleshooting

- **Prompt no encontrado** → versión/capability inválida o archivo no existe → revisar rutas en `loader.py` y estructura en `app/prompts/`.
- **Tokens sin reemplazar (`{context}` queda literal)** → faltan kwargs o el frontmatter no declara ese input → revisar frontmatter del `.md` y el llamado a `format()`.
- **Frontmatter inválido** → formato roto (separadores, claves) → revisar encabezado del `.md` y el parser en `loader.py`.
- **Se carga la versión equivocada** → `version` no llega desde settings o se hardcodeó mal → revisar el punto donde se construye `PromptLoader`.
- **Cambios rompen producción** → se editó una versión usada → crear `vN+1` y apuntar el setting a la nueva versión.

## 🔎 Ver también

- `../../prompts/README.md` (catálogo de prompts)
- `../../prompts/rag_answer/README.md` (prompts de respuesta RAG)
- `../../infrastructure/llm/README.md` (servicio que consume prompts, si aplica)
