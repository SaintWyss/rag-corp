# Infra: Prompts Assets

## 🎯 Misión

Almacén de "Código en Lenguaje Natural".
Aquí residen las plantillas de prompts que se envían a los LLMs. Separarlos del código Python permite que los "Prompt Engineers" iteren sin tocar el backend.

**Qué SÍ hace:**

- Organiza prompts por caso de uso.
- Mantiene versiones de prompts.

**Qué NO hace:**

- No contiene código ejecutable.

## 🗺️ Mapa del territorio

| Recurso       | Tipo       | Responsabilidad (en humano)                              |
| :------------ | :--------- | :------------------------------------------------------- |
| `policy/`     | 📁 Carpeta | Prompts de gobierno (qué puede y no puede hacer el bot). |
| `rag_answer/` | 📁 Carpeta | Prompts para la generación de respuestas RAG.            |

## ⚙️ ¿Cómo funciona por dentro?

Son archivos de texto plano o Jinja2 (`.txt`, `.md`, `.j2`).
El `Infrastructure/PromptLoader` los lee y la capa de `Application` inyecta las variables (ej: `{{ context }}`).

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Static Assets / Configuration.
- **Consumido por:** `PromptLoader` (Infra).

## 👩‍💻 Guía de uso (Snippets)

### Estructura de archivo (Jinja2)

```jinja
Eres un asistente útil.
Contexto: {{ context }}
Pregunta: {{ query }}
```

## 🧩 Cómo extender sin romper nada

1.  **Versionado:** Si cambias drásticamente un prompt, crea `v2.md` y actualiza la configuración para usar la nueva versión gradualmente.

## 🔎 Ver también

- [Prompt Loader (Infra)](../infrastructure/prompts/README.md)
