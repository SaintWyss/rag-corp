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

## Rotación de `GOOGLE_API_KEY`

### 1) Generar nueva key
- Crear/rotar la key en el proveedor correspondiente.

### 2) Actualizar secretos en entornos
- **Local dev:** actualizar el `.env` local (no versionado).
- **CI:** actualizar `GOOGLE_API_KEY` en Secrets del repositorio/entorno.
- **K8s:** actualizar el Secret (`ragcorp-secrets`) o el ExternalSecret.

### 3) Desplegar y validar
- Redeploy del backend/worker.
- Verificar:
  - `/healthz` y `/readyz`
  - logs sin errores de “missing API key”
  - endpoints que usan LLM/embeddings funcionan

---

## Rotación de `JWT_SECRET`

### 1) Generar nuevo secreto
- Usar un secreto fuerte (>= 32 caracteres) y aleatorio.

### 2) Actualizar secretos en entornos
- **Local dev:** actualizar `.env` local (no versionado).
- **CI:** actualizar secrets del entorno.
- **K8s:** actualizar Secret (o ExternalSecret) que alimenta `JWT_SECRET`.

### 3) Invalidar sesiones
- Todos los JWT previos dejarán de ser válidos.
- Comunicar cambio a usuarios si aplica.
- Recomendar re-login.

### 4) Desplegar y validar
- Redeploy del backend.
- Verificar:
  - Auth y endpoints protegidos
  - métricas/health checks

---

## Dónde cargar secretos

- **Local dev:** `.env` local (NO versionado). Usar `.env.example` como plantilla.
- **CI:** GitHub Secrets (`Settings → Secrets and variables`).
- **K8s:** `infra/k8s/secret.yaml` como plantilla o External Secrets.

---

## Referencias

- `docs/runbook/observability.md`
- `infra/k8s/secret.yaml`
- `apps/backend/app/crosscutting/config.py`
