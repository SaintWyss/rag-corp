# Runbooks Frontend

Guía rápida para debuggear problemas comunes en el frontend.

## Auth / Login

**Síntoma:** redirect loop a `/login`.
- Revisar `middleware.ts` (cookies y `/auth/me`).
- Confirmar que `JWT_COOKIE_NAME` coincide con backend.
- Verificar `AUTH_ME_TIMEOUT_MS` (timeouts muy bajos generan loop).

**Síntoma:** admin ve `/workspaces` o employee ve `/admin`.
- Revisar `middleware.ts` (`isWrongPortal`).
- Revisar `src/app-shell/guards/AdminGuard.tsx`.

## Streaming / Chat SSE

**Síntoma:** streaming se corta o nunca completa.
- Revisar `useRagChat` (`STREAM_TIMEOUT_MS`, `MAX_STREAM_CHARS`, `MAX_STREAM_EVENTS`).
- Validar que el backend emita eventos `token/sources/done`.
- Confirmar que `Content-Type` y `Transfer-Encoding` permitan SSE.

**Síntoma:** error "Respuesta demasiado grande".
- Ajustar límites en `useRagChat`.
- Revisar tamaño de chunks o `top_k`.

## Rewrites / API

**Síntoma:** `/api/*` o `/auth/*` devuelve 404.
- Verificar `next.config.mjs` (rewrites).
- Confirmar `RAG_BACKEND_URL`.
- Asegurar que backend exponga `/v1/*` y `/auth/*`.

**Síntoma:** `/api/admin/*` falla.
- Verificar rewrite `/api/admin/* -> /admin/*`.
- Confirmar permisos admin en backend.
