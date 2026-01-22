# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder

WORKDIR /app

RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/package.json
COPY shared/contracts/package.json shared/contracts/package.json
RUN pnpm install --frozen-lockfile

COPY frontend/ ./frontend/
COPY shared/ ./shared/

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN pnpm -C frontend build

# --- Production image ---
FROM node:20-alpine AS production

WORKDIR /app

RUN corepack enable pnpm && \
    addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/frontend/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
