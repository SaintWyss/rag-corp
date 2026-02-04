#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# TARJETA CRC - scripts/security/verify_no_secrets.sh (Verificador de secretos)
# =============================================================================
# Responsabilidades:
# - Detectar secretos accidentales en archivos trackeados (git) sin imprimir valores.
# - Bloquear staging de archivos .env no-example.
# - Proveer mensajes de correccion claros y accionables.
#
# Colaboradores:
# - .gitignore (reglas de exclusion de .env)
# - CI (.github/workflows/ci.yml)
# - docs/runbook/security-rotation.md (rotacion de secretos)
#
# Invariantes:
# - NO imprimir valores de secretos.
# - Solo listar rutas; nunca contenido sensible.
# =============================================================================

readonly PLACEHOLDER_REGEX='(YOUR_|CHANGE_ME|REPLACE|DUMMY|FAKE|EXAMPLE|INSERT|<|\$\{)'

fail=false
bad_paths=()

check_key() {
  local key="$1"

  # Usamos git grep para solo archivos trackeados.
  # Formato: path:line:content
  while IFS=: read -r path _line rest; do
    # Extraemos el valor sin imprimirlo.
    local value
    value="${rest#*=}"
    # Permitimos valores vacios o placeholders.
    if [[ -z "${value}" ]] || [[ "${value}" =~ ${PLACEHOLDER_REGEX} ]]; then
      continue
    fi
    bad_paths+=("${path}")
    fail=true
  done < <(git grep -n -I "${key}=" || true)
}

check_key "GOOGLE_API_KEY"
check_key "JWT_SECRET"

# Detectar .env no-example en staging (index)
while IFS= read -r path; do
  case "${path}" in
    *.env | *.env.*)
      case "${path}" in
        *.env.example | *.env.*.example) ;; # permitido
        *)
          bad_paths+=("${path}")
          fail=true
          ;;
      esac
      ;;
  esac
done < <(git diff --cached --name-only --diff-filter=ACMRT)

if [[ "${fail}" == "true" ]]; then
  echo "[verify_no_secrets] Se detectaron secretos o archivos .env no permitidos."
  echo "[verify_no_secrets] Corrija y reintente. Rutas afectadas:"
  printf '%s\n' "${bad_paths[@]}" | sort -u
  echo ""
  echo "Acciones sugeridas:"
  echo "- Reemplazar valores por placeholders en archivos trackeados."
  echo "- Mover secretos a .env local (no versionado) o a secrets del entorno (CI/K8s)."
  echo "- Asegurar que .env no-example no quede en el staging de git."
  exit 1
fi

echo "[verify_no_secrets] OK"
