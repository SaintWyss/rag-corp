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

export { normalizeProblem } from "./problem";
export type { ApiProblem } from "./problem";

export { parseAuthMe } from "./auth";
export type { AuthMe, AuthRole } from "./auth";
