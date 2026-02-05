/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/contracts/workspaces.ts (Workspace contratos)
===============================================================================
Responsabilidades:
  - Exponer constantes de visibilidad de workspace para el UI.
  - Mantener valores alineados al contrato OpenAPI/back-end.

Colaboradores:
  - shared/contracts/openapi.json

Invariantes:
  - No agregar lógica ni side-effects.
  - Mantener los valores en sync con el backend.
===============================================================================
*/

export const WorkspaceVisibility = {
  PRIVATE: "PRIVATE",
  ORG_READ: "ORG_READ",
  SHARED: "SHARED",
} as const;

export type WorkspaceVisibility =
  typeof WorkspaceVisibility[keyof typeof WorkspaceVisibility];
