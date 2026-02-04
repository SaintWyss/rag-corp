# ADR-001: Single Shared UI Location

## Status
Accepted

## Context
UI components estaban distribuidos entre `app/components`, `src/components` y `src/shared/ui`, lo que generaba duplicación y paths inconsistentes.

## Decision
Centralizar UI reutilizable en `src/shared/ui/` y mover shells a `src/shared/ui/shells`.

## Consequences
- Imports consistentes y menor drift.
- Se eliminan duplicados en `app/components` y `src/components`.
- Lint/arquitectura refuerzan la regla de dependencia.
