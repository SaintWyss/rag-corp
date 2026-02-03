# ============================================================
# TARJETA CRC (Class / Responsibilities / Collaborators)
# ============================================================
# Class: apps/frontend/Dockerfile (Build + Runtime de Next.js en monorepo pnpm)
#
# Responsibilities:
# - Construir la app Next.js (standalone) con pnpm workspaces.
# - Proveer target dev con hot reload para uso local.
# - Generar imagen final minima (standalone) y no-root.
# - Inyectar RAG_BACKEND_URL en build para rewrites/middleware.
#
# Collaborators:
# - pnpm (workspaces + lockfile)
# - Next.js (build + start)
# - shared/contracts (tipos/cliente generado)
# - Docker buildkit (cache de capas)
# ============================================================

# syntax=docker/dockerfile:1.6

# Pinned pnpm version for deterministic builds (aligns with root package.json)
ARG PNPM_VERSION=10.0.0

# ============================================================
# STAGE: deps
# - Instala deps del workspace frontend (cacheable).
# ============================================================
FROM node:20-alpine AS deps

ARG PNPM_VERSION

# ----------------------------
# Configuracion de pnpm
# ----------------------------
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV NEXT_TELEMETRY_DISABLED=1

# Habilita corepack y fija version exacta de pnpm
RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate

# Fija el store de pnpm dentro del contenedor (mejor cache de capas)
RUN pnpm config set store-dir /pnpm/store

WORKDIR /app

# ----------------------------
# Manifiestos del monorepo
# (primero manifests -> mejor cache)
# ----------------------------
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY shared/contracts/package.json shared/contracts/package.json

# Instala deps necesarias para build (dev + prod)
# - Filtra solo el workspace frontend y sus deps
# - Cachea store de pnpm entre builds (BuildKit)
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store,sharing=locked \
    pnpm install --frozen-lockfile --filter ./apps/frontend...

# ============================================================
# STAGE: builder
# - Copia fuentes y ejecuta `next build` (standalone).
# ============================================================
FROM deps AS builder

# ----------------------------
# Variables server-only para rewrites/middleware (bakeadas en build)
# ----------------------------
ARG RAG_BACKEND_URL=http://rag-api:8000
ENV RAG_BACKEND_URL=${RAG_BACKEND_URL}

# ----------------------------
# Codigo fuente
# ----------------------------
COPY apps/frontend/ ./apps/frontend/
COPY shared/ ./shared/

# Elimina archivos .env locales para forzar que el build dependa
# de variables inyectadas por Docker (ARG/ENV) y no por archivos
RUN rm -f apps/frontend/.env apps/frontend/.env.local apps/frontend/.env.* || true

# Compilacion de Next.js (desde workspace)
RUN pnpm -C apps/frontend build

# ============================================================
# STAGE: dev
# - Hot reload para desarrollo local (no es la imagen final).
# ============================================================
FROM deps AS dev

ARG RAG_BACKEND_URL=http://rag-api:8000
ENV RAG_BACKEND_URL=${RAG_BACKEND_URL}

COPY apps/frontend/ ./apps/frontend/
COPY shared/ ./shared/

EXPOSE 3000
CMD ["pnpm", "-C", "apps/frontend", "dev", "--hostname", "0.0.0.0", "--port", "3000"]

# ============================================================
# STAGE: production
# - Runtime minimo usando output: "standalone".
# ============================================================
FROM node:20-alpine AS production

# ----------------------------
# Variables runtime
# ----------------------------
ARG RAG_BACKEND_URL=http://rag-api:8000
ENV RAG_BACKEND_URL=${RAG_BACKEND_URL}

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Seguridad: correr como usuario no-root
RUN addgroup -g 1001 -S app && adduser -S app -u 1001 -G app

WORKDIR /app/apps/frontend

# ----------------------------
# Copia artefactos standalone desde builder
# ----------------------------
COPY --from=builder --chown=app:app /app/apps/frontend/.next/standalone ./
COPY --from=builder --chown=app:app /app/apps/frontend/.next/static ./.next/static
COPY --from=builder --chown=app:app /app/apps/frontend/public ./public

USER app

EXPOSE 3000

# ----------------------------
# Runtime
# ----------------------------
CMD ["node", "server.js"]
