#!/usr/bin/env bash
set -euo pipefail

PORT=9323
MAX_PORT=9350

is_port_free() {
  python3 - <<PY >/dev/null 2>&1
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", int("$1")))
s.close()
PY
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Looking for free port for Playwright report..."
while [ "$PORT" -le "$MAX_PORT" ]; do
  if is_port_free "$PORT"; then
    echo "Found free port: $PORT"
    exec pnpm -C "$E2E_DIR" exec playwright show-report --port "$PORT"
  fi
  echo "Port $PORT in use, trying next..."
  PORT=$((PORT+1))
done

echo "Error: Could not find free port in range 9323-$MAX_PORT"
exit 1
