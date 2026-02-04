/**
 * Documents feature module
 *
 * This module re-exports document-related functions from the shared API client.
 */

export {
    deleteWorkspaceDocument,
    getWorkspaceDocument,
    listWorkspaceDocuments,
    reprocessWorkspaceDocument,
    uploadWorkspaceDocument,
    type DocumentDetail,
    type DocumentSort,
    type DocumentStatus,
    type DocumentSummary,
    type DocumentsListResponse,
    type ListDocumentsParams,
    type ReprocessDocumentResponse,
    type UploadDocumentResponse
} from "@/shared/api/api";
