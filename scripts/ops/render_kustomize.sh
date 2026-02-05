#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# TARJETA CRC - scripts/ops/render_kustomize.sh (Render Kustomize sin kubectl)
# =============================================================================
# Responsabilidades:
# - Renderizar overlays Kustomize via Docker, sin depender de kubectl local.
# - Evitar escribir archivos en el repo (stdout por defecto).
#
# Colaboradores:
# - infra/k8s/overlays/*
#
# Invariantes:
# - No imprimir secretos.
# - Solo usar rutas del repo.
# =============================================================================

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 <staging|prod>" >&2
  exit 1
fi

ENVIRONMENT="$1"
case "$ENVIRONMENT" in
  staging|prod) ;;
  *)
    echo "Entorno invalido: $ENVIRONMENT (usar staging|prod)" >&2
    exit 1
    ;;
esac

OVERLAY_PATH="infra/k8s/overlays/${ENVIRONMENT}"
if [[ ! -d "$OVERLAY_PATH" ]]; then
  echo "Overlay no encontrado: $OVERLAY_PATH" >&2
  exit 1
fi

IMAGE="kustomize/kustomize:v5.4.3"

exec docker run --rm \
  -v "${PWD}:/workdir" \
  -w /workdir \
  "$IMAGE" build "$OVERLAY_PATH"
