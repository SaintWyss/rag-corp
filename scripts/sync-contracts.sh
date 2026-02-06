#!/bin/bash
set -e

echo "Regenerando contratos..."
cd apps/backend
python3 scripts/export_openapi.py --out ../../shared/contracts/openapi.json
cd ../..
pnpm contracts:gen

if ! git diff --quiet shared/contracts/; then
  echo "⚠️  Contratos actualizados. Por favor, commitea los cambios:"
  git status shared/contracts/
  exit 1
fi

echo "✅ Contratos sincronizados"
