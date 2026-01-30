# Prompts Directory

## Estructura

Este directorio contiene los **templates de prompts** organizados por funcionalidad (capability).

```
prompts/
├── README.md              # Este archivo
├── policy/                # Contratos de seguridad globales
│   └── secure_contract_es.md
└── rag_answer/            # Prompts para respuestas RAG
    ├── v1_es.md           # Versión básica
    └── v2_es.md           # Versión avanzada con formato estructurado
```

## Convenciones

### Nomenclatura de archivos

```
{version}_{lang}.md
```

- **version**: `v1`, `v2`, `v3`... (regex: `^v\d+$`)
- **lang**: Código ISO 639-1 (`es`, `en`, `pt`, etc.)

### YAML Frontmatter (obligatorio)

Cada archivo debe comenzar con metadatos en formato YAML:

```yaml
---
type: rag_answer # Tipo de prompt (debe coincidir con la carpeta)
version: "2.1" # Versión semántica del contenido
lang: es # Idioma
description: > # Descripción multilinea
  Breve explicación del propósito del prompt.
author: RAG Corp # Autor/equipo responsable
updated: "2026-01-30" # Última actualización
inputs: # Tokens que el código debe proveer
  - context
  - query
---
```

### Tokens de reemplazo

Los prompts usan tokens con llaves simples:

- `{context}` - Contexto recuperado de documentos
- `{query}` - Pregunta del usuario

**Importante:** No uses `str.format()` de Python. El loader usa `.replace()` para evitar conflictos con JSON o código en los prompts.

## Agregar una nueva versión

1. Copia el archivo de la versión anterior
2. Renómbralo con la nueva versión: `v3_es.md`
3. Actualiza el frontmatter (version, updated, description)
4. Modifica el contenido del prompt
5. Prueba con `PROMPT_VERSION=v3` en tu entorno

## Agregar una nueva capability

1. Crea una nueva carpeta: `prompts/summarization/`
2. Crea el primer template: `v1_es.md` con frontmatter apropiado
3. Actualiza el loader si es necesario (agregar constante de directorio)

## Seguridad

- El **Policy Contract** (`policy/secure_contract_es.md`) se incluye automáticamente antes de cualquier template
- Define reglas anti prompt-injection y jerarquía de instrucciones
- **NUNCA** modifiques las reglas de seguridad sin revisión del equipo
