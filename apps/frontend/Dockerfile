# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder

WORKDIR /app
RUN corepack enable pnpm

# Monorepo manifests
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY shared/contracts/package.json shared/contracts/package.json

# Install (dev+prod) for build
RUN pnpm install --frozen-lockfile

# Source
COPY apps/frontend/ ./apps/frontend/
COPY shared/ ./shared/

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Build Next.js
RUN pnpm -C apps/frontend build


# ---- Production image ----
FROM node:20-alpine AS production

WORKDIR /app
RUN corepack enable pnpm

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Copy only what we need to install prod deps for the frontend (workspace-aware)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY shared/contracts/package.json shared/contracts/package.json

# Install production deps ONLY for frontend (and its workspace deps)
# Esto asegura que exista `next` en runtime, sin depender del "standalone server.js"
RUN pnpm install --prod --frozen-lockfile --filter ./apps/frontend...

# Copy built app from builder
COPY --from=builder /app/apps/frontend/.next ./apps/frontend/.next
COPY --from=builder /app/apps/frontend/public ./apps/frontend/public

EXPOSE 3000

# Run
CMD ["pnpm", "-C", "apps/frontend", "start", "--port", "3000", "--hostname", "0.0.0.0"]
