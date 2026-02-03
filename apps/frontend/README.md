# Rag Corp Frontend

Next.js app (App Router) for the Rag Corp UI.

## Requirements
- Node 20+
- pnpm 10.x

## Local dev
1. pnpm install (repo root)
2. pnpm -C apps/frontend dev
3. Or run pnpm dev (turbo)

## Environment
Set variables in `apps/frontend/.env` for local dev, or in root `.env` for docker-compose.

- RAG_BACKEND_URL: backend base URL used by rewrites (build-time).
- AUTH_ME_TIMEOUT_MS: timeout for /auth/me in middleware (ms). Default 1500, clamped 250-5000.
- JWT_COOKIE_NAME: auth cookie name used by backend. Default rag_access_token.
- JWT_COOKIE_DOMAIN: optional, allows deleting cookies set with Domain.
- NEXT_PUBLIC_JWT_COOKIE_NAME: deprecated, use JWT_COOKIE_NAME.

## Scripts
- pnpm -C apps/frontend dev
- pnpm -C apps/frontend build
- pnpm -C apps/frontend start
- pnpm -C apps/frontend lint
- pnpm -C apps/frontend test
- pnpm -C apps/frontend test:watch
- pnpm -C apps/frontend test:coverage

## Docker
- docker compose --profile ui up -d --build
- Build arg RAG_BACKEND_URL controls rewrites (evaluated at build time).
- Production image uses Next `output: "standalone"`.
- Dev target: `docker build --target dev -t rag-frontend-dev .`

## Routing contract
- /api/* and /auth/* are reserved for backend proxy.
- /api/admin/* proxies to backend /admin/*.
- /v1/* is optional compatibility shim.
