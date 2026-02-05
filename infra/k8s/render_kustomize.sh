#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# TARJETA CRC - infra/k8s/render_kustomize.sh (Render Kustomize dockerizado)
# =============================================================================
# Responsabilidades:
# - Renderizar overlays Kustomize usando Docker (sin depender de kubectl local).
# - Permitir override de imagenes (sha) sin tocar el repo.
# - Escribir salida a stdout o a un archivo indicado por --out.
# - Fallar con mensajes accionables si falta Docker u overlays.
#
# Colaboradores:
# - infra/k8s/overlays/*
#
# Invariantes:
# - No imprimir secretos.
# - No modificar archivos del repo.
# =============================================================================

usage() {
  cat <<'USAGE' >&2
Uso: infra/k8s/render_kustomize.sh <staging|prod> [--out <ruta>] [--backend-image <ref>] [--frontend-image <ref>]

Ejemplos:
  infra/k8s/render_kustomize.sh staging --out /tmp/ragcorp-staging.yaml
  infra/k8s/render_kustomize.sh prod --out /tmp/ragcorp-prod.yaml
  infra/k8s/render_kustomize.sh prod > /tmp/ragcorp-prod.yaml
  infra/k8s/render_kustomize.sh prod --backend-image ghcr.io/org/ragcorp/backend:sha-<sha> --frontend-image ghcr.io/org/ragcorp/frontend:sha-<sha>
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

ENVIRONMENT="$1"
shift || true

OUT_PATH=""
BACKEND_IMAGE=""
FRONTEND_IMAGE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT_PATH="$2"
      shift 2
      ;;
    --out=*)
      OUT_PATH="${1#--out=}"
      shift
      ;;
    --backend-image)
      BACKEND_IMAGE="$2"
      shift 2
      ;;
    --backend-image=*)
      BACKEND_IMAGE="${1#--backend-image=}"
      shift
      ;;
    --frontend-image)
      FRONTEND_IMAGE="$2"
      shift 2
      ;;
    --frontend-image=*)
      FRONTEND_IMAGE="${1#--frontend-image=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argumento desconocido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

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

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no disponible en PATH. Instalar/activar Docker para render." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker no esta corriendo. Iniciar Docker y reintentar." >&2
  exit 1
fi

IMAGE="${KUSTOMIZE_IMAGE:-registry.k8s.io/kustomize/kustomize:v5.4.3}"

WORKDIR_ROOT="${PWD}"
TEMP_DIR=""

cleanup() {
  if [[ -n "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}
trap cleanup EXIT

if [[ -n "$BACKEND_IMAGE" || -n "$FRONTEND_IMAGE" ]]; then
  TEMP_DIR="$(mktemp -d)"
  mkdir -p "$TEMP_DIR/infra"
  cp -R infra/k8s "$TEMP_DIR/infra/k8s"
  WORKDIR_ROOT="$TEMP_DIR"

  if [[ -n "$BACKEND_IMAGE" ]]; then
    docker run --rm \
      -v "${WORKDIR_ROOT}:/workdir" \
      -w "/workdir/infra/k8s/overlays/${ENVIRONMENT}" \
      "$IMAGE" edit set image "ragcorp/backend=${BACKEND_IMAGE}"
  fi

  if [[ -n "$FRONTEND_IMAGE" ]]; then
    docker run --rm \
      -v "${WORKDIR_ROOT}:/workdir" \
      -w "/workdir/infra/k8s/overlays/${ENVIRONMENT}" \
      "$IMAGE" edit set image "ragcorp/frontend=${FRONTEND_IMAGE}"
  fi
fi

render() {
  docker run --rm \
    -v "${WORKDIR_ROOT}:/workdir" \
    -w /workdir \
    "$IMAGE" build --load-restrictor=LoadRestrictionsNone \
    "/workdir/infra/k8s/overlays/${ENVIRONMENT}"
}

if [[ -n "$OUT_PATH" ]]; then
  mkdir -p "$(dirname "$OUT_PATH")"
  render > "$OUT_PATH"
  if [[ ! -s "$OUT_PATH" ]]; then
    echo "Render vacio: $OUT_PATH" >&2
    exit 1
  fi
  echo "Render OK: $OUT_PATH" >&2
else
  render
fi
