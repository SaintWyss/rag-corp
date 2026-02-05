/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/contracts/index.ts (Contracts)
===============================================================================
Responsabilidades:
  - Re-exportar contratos y decoders de API.

Colaboradores:
  - shared/api/api.ts
===============================================================================
*/

export type { AuthMe, AuthRole } from "./auth";
export { parseAuthMe } from "./auth";
export type { ApiProblem } from "./problem";
export { normalizeProblem } from "./problem";
