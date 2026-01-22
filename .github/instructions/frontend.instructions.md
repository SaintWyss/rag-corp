```md
---
applyTo: "frontend/**"
---

# Frontend (Next.js App Router) — reglas específicas del repo (v6)

## Estado / Versión (v6)
- La versión vigente del proyecto/documentación es **v6**.
- “v4” solo puede aparecer como **HISTORICAL** (origen/especificación pasada), claramente marcado.

## Modo de trabajo
- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Source of Truth (anti-drift)
Antes de afirmar algo “como cierto” en FE (paths, endpoints, scripts), verificar en este orden:
1) `shared/contracts/openapi.json` + `shared/contracts/src/generated.ts`
2) `frontend/next.config.ts` (rewrites/proxy)
3) `package.json` / `pnpm` scripts (root y frontend)
4) Docs vigentes v6 (`doc/system/...`, `doc/api/http-api.md`)

## Contratos compartidos (fuente de verdad)
- No duplicar DTOs ni endpoints: usar **`@contracts`** (`shared/contracts/src/generated.ts`).
- Si cambia el API del backend, regenerar contracts (OpenAPI → Orval) y ajustar el frontend en el mismo cambio.

## Acceso a API (proxy actual)
- Las funciones generadas por Orval usan URLs **relativas** (sin host) como `/v1/...`, `/auth/...` o `/api/...` según el rewrite vigente.
- En dev, el proxy está en `frontend/next.config.ts` (verificar reglas reales):
  - `/auth/*` → `${NEXT_PUBLIC_API_URL}/auth/*`
  - `/api/*` → `${NEXT_PUBLIC_API_URL}/v1/*`
  - `/v1/*` → `${NEXT_PUBLIC_API_URL}/v1/*` (compat)
- No hardcodear `http://localhost:8000` en componentes/hooks: mantener llamadas relativas para que el proxy funcione.
- Si se requiere auth:
  - Header esperado: `X-API-Key` (si aplica en v6).
  - No hardcodear claves en repo; usar env (`NEXT_PUBLIC_*`) o un input de UI según corresponda.
  - Nunca guardar API keys humanas en `localStorage` si el hardening v6 lo prohíbe; preferir cookies/headers efímeros o almacenamiento más seguro según implementación real.

## Regla v6 (si aplica): scoping por workspace
- Si la UI consulta/gestiona documentos o chat, debe incluir/selectear `workspace_id` y respetar permisos:
  - owner/admin: write (upload/delete/reprocess)
  - viewer: read + chat
- Endpoints canónicos (si existen): `/v1/workspaces/{id}/...`
- Endpoints legacy (si existen): **DEPRECATED** y siempre con `workspace_id` explícito (nunca implícito).

## Arquitectura UI
- Mantener separación:
  - UI: `frontend/app/components/**`
  - Lógica de red/estado: `frontend/app/hooks/**`
  - `frontend/app/page.tsx`: composición (no lógica compleja).
- Errores:
  - Mapear por status code (ya existe patrón en `frontend/app/hooks/useRagAsk.ts`).
  - No mostrar stack traces; mensajes claros para usuario.
  - Si el backend usa RFC7807 (`application/problem+json`), mapear `title/detail/status` a mensajes de UI consistentes.

## Calidad (CI)
- Lint: `pnpm lint`
- Typecheck: `pnpm tsc --noEmit`
- Tests: `pnpm test --coverage` (Jest en `frontend/__tests__`).
- No commitear coverage: está ignorado por `frontend/.gitignore` (`/coverage`).

## Comandos de validación (cuando aplique)
- `cd frontend && pnpm install --frozen-lockfile && pnpm lint && pnpm tsc --noEmit`
- `cd frontend && pnpm test --coverage`
```