# Deploy Runbook

## Prerequisitos

- Docker + Docker Compose v2
- Variables de entorno configuradas (ver `.env.example`)
- Acceso a Google Cloud API (para embeddings/LLM)

## Variables de entorno requeridas

```bash
# .env.prod
DATABASE_URL=postgresql://ragcorp:SECRET@postgres:5432/ragcorp
POSTGRES_USER=ragcorp
POSTGRES_PASSWORD=SECRET
POSTGRES_DB=ragcorp
GOOGLE_API_KEY=your-google-api-key
NEXT_PUBLIC_API_URL=http://localhost:8000
LOG_LEVEL=info
```

## Deploy con Docker Compose

### 1. Build y start

```bash
# Copiar y editar variables
cp .env.example .env.prod

# Build imágenes
docker compose -f compose.prod.yaml build

# Start servicios
docker compose -f compose.prod.yaml --env-file .env.prod up -d
```

### 2. Verificar salud

```bash
# Check servicios
docker compose -f compose.prod.yaml ps

# Health checks
curl http://localhost:8000/healthz
curl http://localhost:3000
```

### 3. Ver logs

```bash
docker compose -f compose.prod.yaml logs -f backend
docker compose -f compose.prod.yaml logs -f frontend
```

## Rollback

```bash
# Stop servicios
docker compose -f compose.prod.yaml down

# Volver a imagen anterior (si existe tag)
docker compose -f compose.prod.yaml up -d --no-build
```

## Troubleshooting

### Backend no conecta a Postgres

1. Verificar que postgres esté healthy: `docker compose ps`
2. Verificar DATABASE_URL en .env.prod
3. Revisar logs: `docker compose logs postgres`

### Frontend no conecta a Backend

1. Verificar NEXT_PUBLIC_API_URL
2. Verificar que backend esté healthy
3. Revisar network: `docker network ls`

### Out of memory

1. Ajustar limits en compose.prod.yaml
2. Verificar recursos del host: `docker stats`
