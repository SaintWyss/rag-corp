```md
# Instrucciones del proyecto (RAG Corp)

## Estado / Versión (v6)
- La versión vigente del proyecto/documentación es **v6**.
- “v4” solo puede aparecer como **HISTORICAL** (origen/especificación pasada), claramente marcado.

## Source of Truth (anti-drift)
Antes de afirmar algo “como cierto”, verificar en este orden:
1) **Informe de Sistemas v6 (Definitivo)** (`doc/system/informe_de_sistemas_rag_corp.md`).
2) **Contrato API**: `shared/contracts/openapi.json` (y cliente generado si aplica).
3) **DB/Migraciones**: `backend/alembic/versions/*` + `doc/data/postgres-schema.md`.
4) **Runtime real**: `compose*.yaml`, `package.json`, CI workflows, `frontend/next.config.ts`, `backend/app/main.py`/`routes.py`.
5) **Decisiones**: `doc/architecture/decisions/ADR-*.md`.

## Principios
- Prioridad: **calidad, claridad, arquitectura, patrones, testabilidad y mantenimiento**.
- Cambios incrementales (pequeños y revisables). Evitar refactors masivos.
- Aplicar **SOLID** y separación de responsabilidades con límites claros entre capas.

## Veracidad / No alucinaciones
- No inventar features/tests/carpetas/paths. Si no existe en el repo, marcar como **TODO/Planned**.
- Antes de afirmar rutas/endpoints/comandos: verificar en el código, en `compose*.yaml`, contratos (`openapi.json`) y docs existentes.
- Si no se puede verificar, **asumir lo mínimo** y dejar la suposición explícita en **1 línea**.

## Modo anti-spam
- Nunca pegar archivos completos en el chat.
- Editar archivos con **diff/patch**.
- En el chat: solo **archivos tocados + resumen (≤10 bullets) + comandos de validación**.

## Modo de trabajo (ejecución directa)
- **Ejecutar** cambios directamente: no preguntar “¿es lo que querés?” ni pedir confirmación.
- **No hacer planeamiento** ni listas de “opciones”, salvo ambigüedad real o riesgo alto.
- Si falta una decisión menor, **elegir la opción más segura y coherente** con el repo y continuar.
- Solo pedir aclaración cuando:
  - haya **ambigüedad bloqueante** (dos interpretaciones igualmente plausibles),
  - implique un **cambio destructivo** (pérdida de datos / breaking compat),
  - o haya **riesgo de seguridad**.

## Naming / Semántica v6 (consistencia)
- “Workspace” es el término técnico (API/DB/código). “Sección” es **solo UI copy** (si aplica).
- Visibilidad (si está en v6): `PRIVATE | ORG_READ | SHARED` (+ `workspace_acl`).
- Endpoints canónicos (si existen): `/v1/workspaces/{id}/...`
- Endpoints legacy (si existen): **DEPRECATED** y siempre con `workspace_id` explícito (nunca implícito).

## Documentación
- `README.md` raíz como portal y `doc/README.md` como índice.
- Arquitectura en `doc/architecture/overview.md`.
- API en `doc/api/http-api.md` (alineado a `shared/contracts/openapi.json`).
- Datos en `doc/data/postgres-schema.md` (alineado a `backend/alembic/`).
- Runbook en `doc/runbook/local-dev.md`.
- Si un cambio impacta docs, **actualizarlas en el mismo commit**.
- Si hay docs viejos que contradicen v6, marcarlos como **HISTORICAL/Deprecated** o reemplazarlos.

## Git (flujo v6)
- **NO crear ramas ni PRs por defecto.** Trabajar en la rama actual.
- **1 tarea/prompt = 1 commit** (salvo que el prompt pida explícitamente dividir).
- Usar **Conventional Commits**.
- **Sí hacer commit automáticamente** cuando el prompt indique “hacer cambios y commitear” (o cuando el objetivo sea cerrar un área completa).
- **No hacer push** salvo que el prompt lo pida explícitamente.
- `git add -p` recomendado si hay mezcla accidental de cambios.
- Si el repo usa “hitos” (`doc/hitos/*`), actualizarlo solo cuando aplique (sin asumir nombre de rama).
```
