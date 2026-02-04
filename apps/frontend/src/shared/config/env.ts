/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/config/env.ts (Env tipada)
===============================================================================
Responsabilidades:
  - Exponer lectura tipada de variables de entorno usadas en el frontend.
  - Definir defaults seguros si faltan env vars.

Colaboradores:
  - shared/api/api.ts

Notas / Invariantes:
  - Solo leer variables públicas (NEXT_PUBLIC_*) en runtime client.
===============================================================================
*/

function toNumber(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const env = {
  apiTimeoutMs: toNumber(
    process.env.NEXT_PUBLIC_API_TIMEOUT_MS ?? process.env.API_TIMEOUT_MS,
    30_000
  ),
  nodeEnv: process.env.NODE_ENV ?? "development",
};
