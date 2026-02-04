<!--
===============================================================================
TARJETA CRC - docs/runbook/dr-continuity.md
===============================================================================
Responsabilidades:
- Definir estrategia de continuidad y DR con RPO/RTO placeholder.
- Documentar pasos de recuperacion y verificacion.

Colaboradores:
- docs/runbook/backup-restore.md
- docs/runbook/rollback.md
- docs/runbook/worker.md

Invariantes:
- No incluir secretos ni credenciales reales.
- RPO/RTO deben alinearse con negocio y sistema.
===============================================================================
-->
# DR y Continuidad Operativa

**Audiencia:** SRE/DevOps
**Objetivo:** establecer un flujo de recuperacion ante incidentes severos.

---

## Objetivos RPO/RTO (placeholders)

- **RPO objetivo:** TBD (definir con negocio/IT).
- **RTO objetivo:** TBD (definir con negocio/IT).

Referencia: `docs/project/informe_de_negocio_brd_srs_rag_corp.md`.

---

## Alcance

- Postgres, Redis, backend, worker, frontend.

---

## Procedimiento alto nivel (DR)

1) Declarar incidente y congelar despliegues.
2) Restaurar Postgres (ver `docs/runbook/backup-restore.md`).
3) Restaurar Redis (si aplica) y reiniciar backend/worker.
4) Re-deploy de servicios (Helm o GitOps).
5) Reprocesar documentos pendientes (endpoint reprocess).
6) Verificar salud y funcionamiento.

---

## Verificacion tecnica

### Base de datos

```bash
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Healthchecks

```bash
curl "$API_URL/healthz"
curl "$API_URL/readyz"
```

### Reprocesamiento de documentos (validacion funcional)

```bash
curl -X POST "$API_URL/workspaces/$WORKSPACE_ID/documents/$DOCUMENT_ID/reprocess" \
  -H "Authorization: Bearer <token>"
```

Opcional: validar estado del documento via API de documentos.

---

## Notas

- Si hubo migraciones, coordinar rollback con restore.
- Ver `docs/runbook/rollback.md` para el procedimiento de rollback.

