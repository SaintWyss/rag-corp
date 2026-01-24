/**
 * Chat feature module
 *
 * This module re-exports chat/query-related functions from the shared API client
 * and RAG hooks.
 */

export {
    queryWorkspace,
    type QueryWorkspacePayload,
    type QueryWorkspaceResponse
} from "@/shared/api/api";

// RAG hooks for chat functionality
export { useRagAsk } from "@/features/rag/useRagAsk";
export { useRagChat } from "@/features/rag/useRagChat";

