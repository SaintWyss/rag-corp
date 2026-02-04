<!--
===============================================================================
TARJETA CRC - docs/index/ops.md
===============================================================================
Responsabilidades:
- Enumerar los runbooks operativos y sus enlaces canonicos.
- Servir como indice para operacion y continuidad.

Colaboradores:
- docs/runbook/*

Invariantes:
- Mantener enlaces actualizados a runbooks activos.
===============================================================================
-->
# Indice de operaciones
Runbooks y operacion del backend.

## Local y despliegue
- Desarrollo local → `../runbook/local-dev.md`
- Deploy (genérico) → `../runbook/deploy.md`
- Deployment (detalles) → `../runbook/deployment.md`
- Kubernetes → `../runbook/kubernetes.md`
- Docker (contenedores) → `../docker/README.md`

## Runtime
- Worker (jobs) → `../runbook/worker.md`
- Observabilidad → `../runbook/observability.md`
- Troubleshooting → `../runbook/troubleshooting.md`
- Incidentes → `../runbook/incident.md`

## Continuidad y seguridad
- Backup/Restore → `../runbook/backup-restore.md`
- Rollback → `../runbook/rollback.md`
- DR/Continuidad → `../runbook/dr-continuity.md`
- Rotacion de secretos → `../runbook/security-rotation.md`

## Backend operativo
- Root operativo → `../../apps/backend/README.md`
- Worker (README) → `../../apps/backend/app/worker/README.md`
- Scripts → `../../apps/backend/scripts/README.md`
