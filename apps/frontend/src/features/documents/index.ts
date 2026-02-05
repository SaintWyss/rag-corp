/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/documents/index.ts (Feature documentos)
===============================================================================
Responsabilidades:
  - Re-exportar API pública de documentos para el feature.
  - Mantener el contrato de imports estable para consumidores internos.

Colaboradores:
  - shared/api/api.ts

Invariantes:
  - No implementar lógica; solo re-exports.
===============================================================================
*/

export {
  deleteWorkspaceDocument,
  type DocumentDetail,
  type DocumentsListResponse,
  type DocumentSort,
  type DocumentStatus,
  type DocumentSummary,
  getWorkspaceDocument,
  type ListDocumentsParams,
  listWorkspaceDocuments,
  type ReprocessDocumentResponse,
  reprocessWorkspaceDocument,
  type UploadDocumentResponse,
  uploadWorkspaceDocument,
} from "@/shared/api/api";
