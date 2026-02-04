<!--
===============================================================================
TARJETA CRC - docs/runbook/security-rotation.md
===============================================================================
Responsabilidades:
- Documentar rotacion segura de secretos criticos.
- Indicar ubicacion de secretos por entorno (local/CI/K8s).

Colaboradores:
- infra/k8s/secret.yaml
- infra/k8s/externalsecrets/*
- apps/backend/app/crosscutting/config.py

Invariantes:
- No incluir secretos reales ni ejemplos con valores sensibles.
===============================================================================
-->
# Security Rotation Runbook — RAG Corp

**Audiencia:** SRE, DevOps, Developers
**Objetivo:** Rotar secretos críticos sin filtrar valores ni interrumpir más de lo necesario.

---

## Alcance

- `GOOGLE_API_KEY` (LLM/embeddings)
- `JWT_SECRET` (firmado/verificación de tokens)

---

## Principios

- **Nunca** versionar secretos reales.
- Rotar en un **secrets manager** o **secrets de CI/K8s**.
- Validar el deploy después de cada rotación.
- Para `JWT_SECRET`, **invalidar sesiones** (tokens previos deben expirar).

---

## Dónde viven los secretos

- **Local dev:** `.env` local (no versionado). Usar `.env.example` como plantilla.
- **CI:** Secrets del repositorio/entorno (GitHub Actions u otro CI).
- **K8s:** Secret real (`ragcorp-secrets`) creado por:
  - External Secrets Operator (recomendado): `infra/k8s/externalsecrets/*`
  - o creación manual controlada.

**Nota:** `infra/k8s/secret.yaml` es **solo plantilla** y **no debe aplicarse**. El kustomize base no la incluye.

---

## Checklist de rotación — `GOOGLE_API_KEY`

1) Generar nueva key en el proveedor correspondiente.
2) Actualizar en:
   - Local dev (`.env` no versionado)
   - CI (Secrets del repo/entorno)
   - K8s (`ragcorp-secrets` via ExternalSecrets o secret manual)
3) Desplegar backend/worker.
4) Verificar:
   - `/healthz` y `/readyz`
   - logs sin errores de “missing API key”
   - endpoints que usan LLM/embeddings funcionan

---

## Checklist de rotación — `JWT_SECRET`

1) Generar un secreto fuerte (>= 32 caracteres) y aleatorio.
2) Actualizar en:
   - Local dev (`.env` no versionado)
   - CI (Secrets del repo/entorno)
   - K8s (`ragcorp-secrets` via ExternalSecrets o secret manual)
3) **Invalidar sesiones** (tokens previos deben expirar).
4) Desplegar backend.
5) Verificar:
   - auth y endpoints protegidos
   - métricas/health checks

---

## Variables sensibles (backend/worker)

El Secret real debe incluir al menos:
- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `JWT_SECRET`
- `API_KEYS_CONFIG` o `RBAC_CONFIG`

Opcionales según runtime:
- `REDIS_URL`
- `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`

---

## Plantillas K8s

- **Template (no aplicar):** `infra/k8s/secret.yaml`
- **ExternalSecrets (recomendado):** `infra/k8s/externalsecrets/*.yaml`

---

## Referencias

- `docs/project/SECURITY.md`
- `apps/backend/app/crosscutting/config.py`
- `infra/k8s/externalsecrets/`
