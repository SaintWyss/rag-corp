# Architecture Decision Records (ADRs)

Este directorio contiene las **Architecture Decision Records (ADRs)** de RAG Corp.

## ¿Qué son los ADRs?

Los ADRs documentan decisiones arquitectónicas significativas junto con:
- El contexto que motivó la decisión
- Las alternativas consideradas
- Las consecuencias esperadas

**Propósito:**
- Preservar el "por qué" detrás de las decisiones técnicas
- Facilitar onboarding de nuevos miembros del equipo
- Proveer contexto para futuras decisiones
- Evitar debates repetitivos sobre decisiones ya tomadas

---

## Índice de ADRs

| ADR | Título | Estado | Fecha |
|-----|--------|--------|-------|
| [000](000-template.md) | Template | Template | - |
| [001](001-gemini-as-llm.md) | Google Gemini como LLM Provider | Accepted | 2025-12-29 |
| [002](002-chunking-strategy.md) | Estrategia de Chunking (900/120) | Accepted | 2025-12-29 |
| [003](003-pgvector-storage.md) | PostgreSQL + pgvector vs Pinecone | Accepted | 2025-12-29 |

---

## Cómo Proponer un Nuevo ADR

### Paso 1: Copiar el Template

```bash
cd doc/architecture/decisions
cp 000-template.md 004-your-decision-title.md
```

**Convención de numeración:**
- Usar número secuencial (siguiente disponible)
- Formato: `XXX-short-kebab-case-title.md`
- Ejemplo: `004-switch-to-openai.md`

### Paso 2: Completar el Contenido

Edita `004-your-decision-title.md` y completa:

1. **Status:** Comenzar con "Proposed"
2. **Context:** Explica el problema y por qué necesitas decidir
3. **Decision:** Estado claro de qué se decidió
4. **Consequences:** Impactos positivos y negativos
5. **Alternatives:** Qué otras opciones consideraste
6. **References:** Links a issues, docs, código

### Paso 3: Revisión

1. Abre un Pull Request con el ADR propuesto
2. Tag: `architecture` + `adr`
3. Solicita revisión de al menos 2 personas del equipo
4. Discute en comentarios del PR

### Paso 4: Aceptación

Una vez aprobado:
1. Cambiar status de "Proposed" → "Accepted"
2. Merge del PR
3. Actualizar la tabla de índice en este README
4. Comunicar la decisión al equipo

---

## Estados de ADRs

| Estado | Significado |
|--------|-------------|
| **Proposed** | En discusión, no aplicado aún |
| **Accepted** | Aprobado e implementado |
| **Deprecated** | Ya no se recomienda, pero no reemplazado formalmente |
| **Superseded** | Reemplazado por otro ADR (incluir link) |

---

## Cuándo Crear un ADR

**✅ Crea un ADR cuando:**
- Cambias de proveedor de LLM/embeddings
- Modificas la arquitectura de capas
- Eliges una nueva tecnología (DB, framework, biblioteca)
- Cambias estrategias de indexación/búsqueda
- Decides sobre autenticación/autorización
- Modificas el modelo de datos

**❌ No creas un ADR para:**
- Fixes de bugs
- Refactors menores sin cambio de arquitectura
- Cambios de configuración triviales
- Actualizaciones de versiones de dependencias

---

## Ejemplos de Buenos ADRs

### Ejemplo Mínimo

```markdown
# ADR-004: Cambiar de Gemini a OpenAI

## Status
Proposed

## Context
Gemini tiene latencia de 2-3s. Necesitamos <500ms para producción.

## Decision
Cambiar a OpenAI GPT-4-turbo (500ms promedio).

## Consequences
✅ Reduce latencia 4x
⚠️ Costo aumenta $0.03 → $0.10 por 1k tokens

## Alternatives
- Mantener Gemini + caching → no resuelve cold starts
- Claude: similar latencia, API menos madura

## References
- Benchmark: benchmarks/latency-comparison.md
```

### Ejemplo Completo

Ver [001-gemini-as-llm.md](001-gemini-as-llm.md)

---

## Actualizar un ADR Existente

**Si el ADR fue Accepted:**
- No modificar el ADR original
- Crear un nuevo ADR que lo supersede
- Actualizar el original con: `Status: Superseded by [ADR-XXX](XXX-title.md)`

**Si el ADR está Proposed:**
- Puedes editar directamente durante la revisión

---

## Recursos Adicionales

- **Michael Nygard's ADRs:** https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- **ADR Tools:** https://github.com/npryce/adr-tools
- **Examples:** https://github.com/joelparkerhenderson/architecture-decision-record

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
