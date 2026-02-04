<!--
===============================================================================
TARJETA CRC - docs/runbook/rollback.md
===============================================================================
Responsabilidades:
- Definir procedimiento de rollback para Helm y GitOps.
- Alinear rollback con politica de migraciones.

Colaboradores:
- docs/runbook/backup-restore.md
- docs/runbook/migrations.md
- infra/helm/ragcorp/README.md

Invariantes:
- No exponer secretos.
- Rollback de schema se resuelve via restore si aplica.
===============================================================================
-->
# Rollback (Helm + GitOps)

**Audiencia:** SRE/DevOps
**Objetivo:** recuperar el servicio ante despliegues fallidos sin cambiar APIs.

---

## Principios

- Migraciones **forward-only**: rollback de schema via restore si aplica.
- Validar salud y endpoints operativos despues de rollback.

---

## Helm rollback

1) Identificar release y namespace.

```bash
helm list -n <namespace>
helm history <release> -n <namespace>
```

2) Ejecutar rollback a una revision estable.

```bash
helm rollback <release> <revision> -n <namespace> --wait
```

3) Verificar despliegue.

```bash
kubectl rollout status deploy/<deployment> -n <namespace>
```

4) Verificar salud.

```bash
curl "$API_URL/healthz"
curl "$API_URL/readyz"
```

---

## GitOps revert

1) Revertir el commit que introdujo el fallo en el repo de deploy.
2) Esperar sincronizacion del controlador GitOps (Argo CD / Flux).
3) Verificar despliegue y salud (igual que Helm).

---

## Si hubo migraciones

- Si una migracion ya se aplico, el rollback de app puede requerir restore.
- Ver `docs/runbook/backup-restore.md` y `docs/runbook/migrations.md`.

