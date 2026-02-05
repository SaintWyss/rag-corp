<!--
===============================================================================
TARJETA CRC - docs/runbook/backup-drill-log.md
===============================================================================
Responsabilidades:
- Registrar evidencia de drills de backup/restore.
- Capturar tiempos reales de RPO/RTO y hallazgos.

Colaboradores:
- docs/runbook/backup-restore.md
- docs/runbook/dr-continuity.md

Invariantes:
- No incluir secretos ni credenciales reales.
===============================================================================
-->
# Backup/Restore Drill — Log de evidencia

**Audiencia:** SRE/DevOps  
**Objetivo:** documentar ejercicios de backup/restore con tiempos medidos.

---

## Registro de drill (plantilla)

- **Fecha:** YYYY-MM-DD
- **Entorno:** staging | prod | otro
- **Responsable:** nombre/equipo
- **Sistema:** Postgres | Redis | Ambos
- **Backup utilizado:** ID/ubicación (sin secretos)
- **Objetivo:** validar restore + smoke

### Tiempos
- **Inicio restore:** HH:MM
- **Fin restore:** HH:MM
- **RTO real:** XX minutos
- **RPO estimado:** XX minutos (según backup y última ventana)

### Verificaciones ejecutadas
- `psql "$DATABASE_URL" -c "SELECT 1;"`
- `curl "$API_URL/healthz"`
- `curl "$API_URL/readyz"`
- Reproceso de documento de prueba (endpoint reprocess)

### Resultado
- **Estado:** OK | NOK
- **Hallazgos:** (1–3 bullets)
- **Acciones de mejora:** (1–3 bullets)

---

## Checklist de cierre

- [ ] RTO dentro del objetivo.
- [ ] RPO dentro del objetivo.
- [ ] Servicios saludables.
- [ ] Hallazgos registrados y accionables.
