```md
---
applyTo: "apps/frontend/**"
---

# Frontend (Next.js App Router) — reglas específicas del repo

## Estado / Versión
- Baseline actual: `docs/project/informe_de_sistemas_rag_corp.md`.
- No usar etiquetas internas de versión en documentación.

## Modo de trabajo
- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Source of Truth (anti-drift)
Antes de afirmar algo “como cierto” en FE (paths, endpoints, scripts), verificar en este orden:
1) `shared/contracts/openapi.json` + `shared/contracts/src/generated.ts`
2) `apps/frontend/next.config.mjs` (rewrites/proxy)
3) `package.json` / `pnpm` scripts (root y frontend)
4) Docs vigentes (`docs/project/informe_de_sistemas_rag_corp.md`, `docs/reference/api/http-api.md`)

## Contratos compartidos (fuente de verdad)
- No duplicar DTOs ni endpoints: usar **`@contracts`** (`shared/contracts/src/generated.ts`).
- Si cambia el API del backend, regenerar contracts (OpenAPI → Orval) y ajustar el frontend en el mismo cambio.

## Acceso a API (proxy actual)
- Las funciones generadas por Orval usan URLs **relativas** (sin host) como `/v1/...`, `/auth/...` o `/api/...` según el rewrite vigente.
- En dev, el proxy está en `apps/frontend/next.config.mjs` (verificar reglas reales):
  - `/auth/*` → `${RAG_BACKEND_URL}/auth/*`
  - `/api/admin/*` → `${RAG_BACKEND_URL}/admin/*`
  - `/api/*` → `${RAG_BACKEND_URL}/v1/*`
  - `/v1/*` → `${RAG_BACKEND_URL}/v1/*`
- No hardcodear `http://localhost:8000` en componentes/hooks: mantener llamadas relativas para que el proxy funcione.
- Si se requiere auth:
  - Header esperado: `X-API-Key` (si aplica).
  - No hardcodear claves en repo; usar env (`NEXT_PUBLIC_*`) o un input de UI según corresponda.
  - Nunca guardar API keys humanas en `localStorage` si el hardening lo prohíbe; preferir cookies/headers efímeros o almacenamiento más seguro según implementación real.

## Regla de scoping por workspace
- Si la UI consulta/gestiona documentos o chat, debe incluir/selectear `workspace_id` y respetar permisos:
  - owner/admin: write (upload/delete/reprocess)
  - viewer: read + chat
- Endpoints canónicos: `/v1/workspaces/{id}/...`

## Arquitectura UI
- Mantener separación:
  - Routing/layouts: `apps/frontend/app/**`
  - UI compartida: `apps/frontend/src/shared/ui/**`
  - Lógica de red/estado: `apps/frontend/src/hooks/**` y `apps/frontend/src/services/**`
- Errores:
- Mapear por status code (ver `apps/frontend/src/features/rag/useRagAsk.ts`).
  - No mostrar stack traces; mensajes claros para usuario.
  - Si el backend usa RFC7807 (`application/problem+json`), mapear `title/detail/status` a mensajes de UI consistentes.

## Calidad (CI)
- Lint: `pnpm lint`
- Typecheck: `pnpm tsc --noEmit`
- Tests: `pnpm test --coverage` (Jest en `frontend/__tests__`).
- No commitear coverage: está ignorado por `apps/frontend/.gitignore` (`/coverage`).

## Comandos de validación (cuando aplique)
- `cd apps/frontend && pnpm install --frozen-lockfile && pnpm lint && pnpm tsc --noEmit`
- `cd apps/frontend && pnpm test --coverage`
```
