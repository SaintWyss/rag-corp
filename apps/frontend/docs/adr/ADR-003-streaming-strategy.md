# ADR-003: Streaming Strategy (SSE)

## Status
Accepted

## Context
El chat necesita streaming de tokens en tiempo real. Debe ser resiliente a timeouts y respuestas demasiado grandes.

## Decision
Usar SSE con parsing incremental, timeout y límites de eventos/caracteres en `useRagChat`.

## Consequences
- Mejor UX (tokens en vivo) y control de recursos.
- AbortController y límites evitan loops o payloads excesivos.
- El parsing SSE se centraliza en `src/shared/api/sse.ts`.
