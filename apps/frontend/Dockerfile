# ============================================================
# TARJETA CRC (Class / Responsibilities / Collaborators)
# ============================================================
# Class: apps/frontend/Dockerfile (Build + Runtime de Next.js en monorepo pnpm)
#
# Responsibilities:
# - Construir la app Next.js (stage builder) con pnpm workspaces.
# - Generar una imagen final (stage production) con solo dependencias runtime.
# - Inyectar NEXT_PUBLIC_API_URL en build para variables públicas del frontend.
#
# Collaborators:
# - pnpm (workspaces + lockfile)
# - Next.js (build + start)
# - shared/contracts (tipos/cliente generado)
# - Docker buildkit (cache de capas)
# ============================================================

# syntax=docker/dockerfile:1

# ============================================================
# STAGE 1: builder
# - Instala deps (incluye dev) para compilar Next.
# - Copia fuentes y ejecuta `next build`.
# ============================================================
FROM node:20-alpine AS builder

# ----------------------------
# Configuración de pnpm
# ----------------------------
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

# Habilita corepack para que pnpm quede versionado/gestionado
RUN corepack enable

# Fija el store de pnpm dentro del contenedor (mejor cache de capas)
RUN pnpm config set store-dir /pnpm/store

WORKDIR /app

# ----------------------------
# Manifiestos del monorepo
# (primero manifests → mejor cache)
# ----------------------------
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY shared/contracts/package.json shared/contracts/package.json

# Instala deps necesarias para build (dev + prod)
# Nota: Podrías hacerlo más eficiente con `--filter` (ver mejoras)
RUN pnpm install --frozen-lockfile

# ----------------------------
# Código fuente
# ----------------------------
COPY apps/frontend/ ./apps/frontend/
COPY shared/ ./shared/

# Elimina archivos .env locales para forzar que el build dependa
# de variables inyectadas por Docker (ARG/ENV) y no por archivos
RUN rm -f apps/frontend/.env apps/frontend/.env.local

# ----------------------------
# Variables públicas de Next (bakeadas en build)
# IMPORTANTE:
# - NEXT_PUBLIC_* se embebe en el bundle cliente.
# - Debe pasarse al build si querés que sea efectiva.
# ----------------------------
ARG NEXT_PUBLIC_API_URL=http://rag-api:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Compilación de Next.js (desde workspace)
RUN pnpm -C apps/frontend build


# ============================================================
# STAGE 2: production
# - Imagen runtime liviana.
# - Instala solo deps de producción para el workspace frontend.
# - Copia artefactos build (.next) y static (public).
# ============================================================
FROM node:20-alpine AS production

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable
RUN pnpm config set store-dir /pnpm/store

WORKDIR /app

# ----------------------------
# Variables runtime
# ----------------------------
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# ----------------------------
# Manifiestos mínimos para instalar deps runtime
# (workspace-aware: frontend + deps del workspace)
# ----------------------------
COPY apps/frontend/next.config.mjs ./apps/frontend/next.config.mjs
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY shared/contracts/package.json shared/contracts/package.json

# Instala SOLO dependencias de producción para el frontend
# - `--filter ./apps/frontend...` incluye el workspace y sus deps workspace
# - Esto asegura que `next` exista en runtime para `pnpm start`
RUN pnpm install --prod --frozen-lockfile --filter ./apps/frontend...

# ----------------------------
# Copia artefactos build desde builder
# ----------------------------
COPY --from=builder /app/apps/frontend/.next ./apps/frontend/.next
COPY --from=builder /app/apps/frontend/public ./apps/frontend/public

EXPOSE 3000

# ----------------------------
# Runtime
# ----------------------------
CMD ["pnpm", "-C", "apps/frontend", "start", "--port", "3000", "--hostname", "0.0.0.0"]