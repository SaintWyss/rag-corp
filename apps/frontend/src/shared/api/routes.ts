/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/routes.ts (API Routes)
===============================================================================
Responsabilidades:
  - Centralizar los endpoints consumidos por el frontend.
  - Evitar strings duplicados y drift entre capas.
  - Proveer helpers para rutas con params.

Colaboradores:
  - shared/api/api.ts
  - features/* (hooks/services)

Notas / Invariantes:
  - Mantener prefijos coherentes: /auth/* y /api/*.
  - Las rutas de negocio siempre son workspace-scoped.
===============================================================================
*/

export const apiRoutes = {
  auth: {
    login: "/auth/login",
    logout: "/auth/logout",
    me: "/auth/me",
    users: "/auth/users",
    user: (userId: string) => `/auth/users/${userId}`,
    disableUser: (userId: string) => `/auth/users/${userId}/disable`,
    resetPassword: (userId: string) => `/auth/users/${userId}/reset-password`,
  },
  admin: {
    workspaces: "/api/admin/workspaces",
    userWorkspaces: (userId: string) => `/api/admin/users/${userId}/workspaces`,
  },
  workspaces: {
    list: "/api/workspaces",
    create: "/api/workspaces",
    byId: (workspaceId: string) => `/api/workspaces/${workspaceId}`,
    publish: (workspaceId: string) =>
      `/api/workspaces/${workspaceId}/publish`,
    share: (workspaceId: string) => `/api/workspaces/${workspaceId}/share`,
    archive: (workspaceId: string) => `/api/workspaces/${workspaceId}/archive`,
    documents: (workspaceId: string) =>
      `/api/workspaces/${workspaceId}/documents`,
    document: (workspaceId: string, documentId: string) =>
      `/api/workspaces/${workspaceId}/documents/${documentId}`,
    uploadDocument: (workspaceId: string) =>
      `/api/workspaces/${workspaceId}/documents/upload`,
    reprocessDocument: (workspaceId: string, documentId: string) =>
      `/api/workspaces/${workspaceId}/documents/${documentId}/reprocess`,
    ingestText: (workspaceId: string) =>
      `/api/workspaces/${workspaceId}/ingest/text`,
    ingestBatch: (workspaceId: string) =>
      `/api/workspaces/${workspaceId}/ingest/batch`,
    query: (workspaceId: string) => `/api/workspaces/${workspaceId}/query`,
    ask: (workspaceId: string) => `/api/workspaces/${workspaceId}/ask`,
    askStream: (workspaceId: string) =>
      `/api/workspaces/${workspaceId}/ask/stream`,
  },
} as const;
