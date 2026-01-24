/**
 * Workspaces feature module
 *
 * This module re-exports workspace-related functions from the shared API client.
 */

export {
    archiveWorkspace, createWorkspace, listWorkspaces, publishWorkspace,
    shareWorkspace, type ArchiveWorkspaceResponse, type CreateWorkspacePayload, type ListWorkspacesParams, type ShareWorkspacePayload, type WorkspaceSummary,
    type WorkspacesListResponse
} from "@/shared/api/api";

