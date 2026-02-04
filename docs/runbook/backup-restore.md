<!--
===============================================================================
TARJETA CRC - docs/runbook/backup-restore.md
===============================================================================
Responsabilidades:
- Definir estrategia minima de backup y restore para Postgres y Redis.
- Documentar verificaciones y pasos de recuperacion.

Colaboradores:
- docs/runbook/migrations.md
- docs/runbook/worker.md
- apps/backend/app/interfaces/api/http/routers/documents.py

Invariantes:
- No incluir secretos ni credenciales reales.
- Usar placeholders en comandos y endpoints.
===============================================================================
-->
# Backup y Restore (Postgres + Redis)

**Audiencia:** SRE/DevOps
**Objetivo:** continuidad operativa con recuperacion verificable.

---

## Alcance

- **Postgres:** datos persistentes del producto.
- **Redis:** cola RQ y estado transitorio de jobs.

---

## Principios

- Backups regulares y restores probados.
- No versionar secretos ni credenciales.
- Validar salud despues de restaurar.

---

## Postgres

### Estrategias recomendadas

- **Backup logico (pg_dump):** portable y verificable.
- **Snapshot administrado:** rapido para DR (si el proveedor lo soporta).

### Backup logico (ejemplo)

```bash
export DATABASE_URL="postgres://USER:PASS@HOST:5432/DB"
pg_dump "$DATABASE_URL" --format=custom --file="/backups/ragcorp-$(date +%F).dump"
```

### Restore logico (ejemplo)

```bash
export DATABASE_URL="postgres://USER:PASS@HOST:5432/DB"
pg_restore --clean --if-exists --dbname="$DATABASE_URL" "/backups/ragcorp-YYYY-MM-DD.dump"
```

### Verificacion post-restore

```bash
psql "$DATABASE_URL" -c "SELECT 1;"
psql "$DATABASE_URL" -c "SELECT now();"
```

---

## Redis / RQ

### Que se pierde si Redis cae

- Jobs en cola y en progreso se pierden.
- El estado persistente de documentos vive en Postgres; se puede reencolar.

### Restore minimo

1) Restaurar Redis (snapshot del proveedor o despliegue nuevo).
2) Reconfigurar `REDIS_URL` en backend/worker.
3) Reiniciar backend y worker.

### Reprocesar jobs (reencolar)

- Usar el endpoint de reproceso de documentos para reencolar.

```bash
curl -X POST "$API_URL/workspaces/$WORKSPACE_ID/documents/$DOCUMENT_ID/reprocess" \
  -H "Authorization: Bearer <token>"
```

### Verificacion de cola

```bash
curl "$API_URL/healthz"
curl "$API_URL/readyz"
```

---

## Checklist post-restore

- `/healthz` y `/readyz` OK (backend y worker).
- Backend/worker levantan sin errores de conexion DB/Redis.
- Reproceso de un documento de prueba confirmado.

