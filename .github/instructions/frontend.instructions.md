---
applyTo: "frontend/**"
---

# Frontend (Next.js App Router) — reglas específicas del repo

## Modo de trabajo
- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Contratos compartidos (fuente de verdad)
- No duplicar DTOs ni endpoints: usar **`@contracts`** (`shared/contracts/src/generated.ts`).
- Si cambia el API del backend, regenerar contracts (OpenAPI → Orval) y ajustar el frontend en el mismo cambio.

## Acceso a API (proxy actual)
- Las funciones generadas por Orval usan URLs relativas como `/v1/...`.
- En dev, el proxy está en `frontend/next.config.ts`:
  - Rewrites: `/v1/*` → `${NEXT_PUBLIC_API_URL}/v1/*` (default `http://127.0.0.1:8000`).
- No hardcodear `http://localhost:8000` en componentes/hooks: mantener llamadas relativas para que el proxy funcione.
- Si se requiere auth:
  - Header esperado: `X-API-Key`.
  - No hardcodear claves en repo; usar env (`NEXT_PUBLIC_*`) o un input de UI según corresponda.

## Arquitectura UI
- Mantener separación:
  - UI: `frontend/app/components/**`
  - Lógica de red/estado: `frontend/app/hooks/**`
  - `frontend/app/page.tsx`: composición (no lógica compleja).
- Errores:
  - Mapear por status code (ya existe patrón en `frontend/app/hooks/useRagAsk.ts`).
  - No mostrar stack traces; mensajes claros para usuario.

## Calidad (CI)
- Lint: `pnpm lint`
- Typecheck: `pnpm tsc --noEmit`
- Tests: `pnpm test --coverage` (Jest en `frontend/__tests__`).
- No commitear coverage: está ignorado por `frontend/.gitignore` (`/coverage`).

## Comandos de validación (cuando aplique)
- `cd frontend && pnpm install --frozen-lockfile && pnpm lint && pnpm tsc --noEmit`
- `cd frontend && pnpm test --coverage`
