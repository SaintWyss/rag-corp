/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/auth/index.ts (Feature auth)
===============================================================================
Responsabilidades:
  - Re-exportar el API público de auth para el feature.
  - Mantener el contrato de imports estable para consumidores internos.

Colaboradores:
  - shared/api/api.ts

Invariantes:
  - No implementar lógica; solo re-exports.
===============================================================================
*/

export { type CurrentUser,getCurrentUser, login, logout } from "@/shared/api/api";
