# ADR-010: Prompt Policy Contract, Injection Detection, and Workspace Scoping

Date: 2026-01-29

## Context
- El sistema RAG usa documentos recuperados como contexto y debe resistir prompt injection.
- Se requiere garantizar aislamiento por `workspace_id` (no existe `section_id`).
- Se deben incluir citas estables y trazables en las respuestas.
- Se necesita observabilidad mínima para seguridad (rechazos, detecciones, scope).

## Decision
1) **Policy Contract central**
   - Archivo: `apps/backend/app/prompts/policy_contract_es.md`
   - Se compone siempre con el template de prompt activo (v1/v2).
   - Define jerarquía de instrucciones, anti‑injection, citas [S#] y no‑exfiltración.

2) **Contexto con citas estables**
   - `ContextBuilder` emite fragmentos [S#] y una sección “FUENTES” con metadata real.

3) **Scoping estricto por workspace**
   - Use cases y repositorio requieren `workspace_id` válido.
   - Operaciones sin scope se rechazan (fail‑fast).

4) **Detector de prompt injection en ingest**
   - Heurístico, sin persistir texto crudo.
   - Metadata por chunk: `security_flags`, `risk_score`, `detected_patterns`.
   - Modos de filtrado: `off` | `downrank` | `exclude`.

5) **Observabilidad**
   - Métricas específicas para rechazos, detecciones y fuentes.

## Alternatives Considered
- **Bloqueo total de chunks con señales de inyección**: descartado por riesgo de falsos positivos.
- **Scoping por sección**: no aplicable, el modelo de datos no tiene `section_id`.
- **Guardar texto completo en metadata**: descartado por riesgo de fuga.

## Consequences
- Mayor seguridad ante inyección/exfiltración con cambios mínimos en el flujo actual.
- Los filtros de inyección pueden reducir recall si se usan modos estrictos.
- Métricas adicionales disponibles para monitoreo de seguridad.

## Definition of Done
- Policy Contract aplicado siempre al prompt final.
- Contexto con [S#] y sección “FUENTES”.
- `workspace_id` obligatorio en API/use cases/repositorio.
- Detector de inyección con metadata y tests unitarios.
- Filtro por modo `off|downrank|exclude` y tests.
- Pack de tests de seguridad (cross‑workspace, no exfiltración).
- Métricas de seguridad expuestas y testeadas.
