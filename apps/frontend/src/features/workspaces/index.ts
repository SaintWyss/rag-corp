/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/workspaces/index.ts (Feature workspaces)
===============================================================================
Responsabilidades:
  - Re-exportar API pública de workspaces para el feature.
  - Mantener el contrato de imports estable para consumidores internos.

Colaboradores:
  - shared/api/api.ts

Invariantes:
  - No implementar lógica; solo re-exports.
===============================================================================
*/

export {
  archiveWorkspace,
  type ArchiveWorkspaceResponse,
  createWorkspace,
  type CreateWorkspacePayload,
  listWorkspaces,
  type ListWorkspacesParams,
  publishWorkspace,
  shareWorkspace,
  type ShareWorkspacePayload,
  type WorkspacesListResponse,
  type WorkspaceSummary,
} from "@/shared/api/api";
