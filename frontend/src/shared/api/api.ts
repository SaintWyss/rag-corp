import { getStoredApiKey } from "@/shared/lib/apiKey";
import type {
    ArchiveWorkspaceRes,
    CreateWorkspaceReq,
    DocumentDetailRes,
    DocumentSummaryRes,
    DocumentsListRes,
    IngestBatchReq,
    IngestBatchRes,
    IngestTextReq,
    IngestTextRes,
    QueryReq,
    QueryRes,
    ReprocessDocumentRes,
    UploadDocumentRes,
    WorkspaceRes,
    WorkspacesListRes,
} from "@contracts/src/generated";

export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";

export type DocumentSummary = Omit<DocumentSummaryRes, "status"> & {
  status?: DocumentStatus | null;
};

export type DocumentDetail = Omit<DocumentDetailRes, "status"> & {
  status?: DocumentStatus | null;
};

export type DocumentsListResponse = Omit<DocumentsListRes, "documents"> & {
  documents: DocumentSummary[];
};

export type DocumentSort =
  | "created_at_desc"
  | "created_at_asc"
  | "title_asc"
  | "title_desc";

export type ListDocumentsParams = {
  q?: string;
  status?: DocumentStatus;
  tag?: string;
  sort?: DocumentSort;
  cursor?: string;
  limit?: number;
};

export type UploadDocumentResponse = UploadDocumentRes;

export type ReprocessDocumentResponse = ReprocessDocumentRes;

export type CurrentUser = {
  id: string;
  email: string;
  role: "admin" | "employee";
  is_active: boolean;
  created_at?: string | null;
};

export type AdminUser = {
  id: string;
  email: string;
  role: "admin" | "employee";
  is_active: boolean;
  created_at?: string | null;
};

export type UsersListResponse = {
  users: AdminUser[];
};

export type CreateUserPayload = {
  email: string;
  password: string;
  role?: "admin" | "employee";
};

export type WorkspaceSummary = WorkspaceRes;

export type WorkspacesListResponse = WorkspacesListRes;

export type ListWorkspacesParams = {
  ownerUserId?: string;
  includeArchived?: boolean;
};

export type CreateWorkspacePayload = CreateWorkspaceReq;

export type ShareWorkspacePayload = {
  user_ids: string[];
};

export type ArchiveWorkspaceResponse = ArchiveWorkspaceRes;

export type QueryWorkspacePayload = QueryReq;

export type QueryWorkspaceResponse = QueryRes;

type ApiError = {
  status: number;
  message: string;
};

function withApiKeyHeaders(headers: HeadersInit = {}): HeadersInit {
  const apiKey = getStoredApiKey();
  if (!apiKey) {
    return headers;
  }
  return {
    ...headers,
    "X-API-Key": apiKey,
  };
}

async function requestJson<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: withApiKeyHeaders(options.headers),
    credentials: "include",
  });

  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) {
    const error = data as { detail?: string; message?: string } | null;
    const message =
      error?.detail ||
      error?.message ||
      `Request failed with status ${res.status}`;
    const apiError: ApiError = { status: res.status, message };
    throw apiError;
  }

  return data as T;
}

export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await requestJson<CurrentUser>("/auth/me", { method: "GET" });
  } catch (err) {
    if (typeof err === "object" && err && "status" in err) {
      const status = (err as ApiError).status;
      if (status === 401) {
        return null;
      }
    }
    throw err;
  }
}

export async function listUsers(): Promise<UsersListResponse> {
  return requestJson<UsersListResponse>("/auth/users", { method: "GET" });
}

export async function createUser(
  payload: CreateUserPayload
): Promise<AdminUser> {
  return requestJson<AdminUser>("/auth/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function disableUser(userId: string): Promise<AdminUser> {
  return requestJson<AdminUser>(`/auth/users/${userId}/disable`, {
    method: "POST",
  });
}

export async function resetUserPassword(
  userId: string,
  password: string
): Promise<AdminUser> {
  return requestJson<AdminUser>(`/auth/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
}

export async function listWorkspaces(
  params: ListWorkspacesParams = {}
): Promise<WorkspacesListResponse> {
  const searchParams = new URLSearchParams();
  if (params.ownerUserId) {
    searchParams.set("owner_user_id", params.ownerUserId);
  }
  if (params.includeArchived) {
    searchParams.set("include_archived", "true");
  }
  const query = searchParams.toString();
  return requestJson<WorkspacesListResponse>(
    `/api/workspaces${query ? `?${query}` : ""}`,
    {
      method: "GET",
    }
  );
}

export async function createWorkspace(
  payload: CreateWorkspacePayload
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function publishWorkspace(
  workspaceId: string
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>(`/api/workspaces/${workspaceId}/publish`, {
    method: "POST",
  });
}

export async function shareWorkspace(
  workspaceId: string,
  payload: ShareWorkspacePayload
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>(`/api/workspaces/${workspaceId}/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function archiveWorkspace(
  workspaceId: string
): Promise<ArchiveWorkspaceResponse> {
  return requestJson<ArchiveWorkspaceResponse>(
    `/api/workspaces/${workspaceId}/archive`,
    {
      method: "POST",
    }
  );
}

function buildDocumentsQuery(params: ListDocumentsParams): string {
  const searchParams = new URLSearchParams();
  if (params.q) {
    searchParams.set("q", params.q);
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  if (params.tag) {
    searchParams.set("tag", params.tag);
  }
  if (params.sort) {
    searchParams.set("sort", params.sort);
  }
  if (params.cursor) {
    searchParams.set("cursor", params.cursor);
  }
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams.toString();
}

export async function listWorkspaceDocuments(
  workspaceId: string,
  params: ListDocumentsParams = {}
): Promise<DocumentsListResponse> {
  const query = buildDocumentsQuery(params);
  return requestJson<DocumentsListResponse>(
    `/api/workspaces/${workspaceId}/documents${query ? `?${query}` : ""}`,
    {
      method: "GET",
    }
  );
}

export async function getWorkspaceDocument(
  workspaceId: string,
  documentId: string
): Promise<DocumentDetail> {
  return requestJson<DocumentDetail>(
    `/api/workspaces/${workspaceId}/documents/${documentId}`,
    {
      method: "GET",
    }
  );
}

export async function deleteWorkspaceDocument(
  workspaceId: string,
  documentId: string
): Promise<void> {
  await requestJson(`/api/workspaces/${workspaceId}/documents/${documentId}`, {
    method: "DELETE",
  });
}

export async function uploadWorkspaceDocument(
  workspaceId: string,
  payload: FormData
): Promise<UploadDocumentResponse> {
  return requestJson<UploadDocumentResponse>(
    `/api/workspaces/${workspaceId}/documents/upload`,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function reprocessWorkspaceDocument(
  workspaceId: string,
  documentId: string
): Promise<ReprocessDocumentResponse> {
  return requestJson<ReprocessDocumentResponse>(
    `/api/workspaces/${workspaceId}/documents/${documentId}/reprocess`,
    {
      method: "POST",
    }
  );
}

export async function queryWorkspace(
  workspaceId: string,
  payload: QueryWorkspacePayload
): Promise<QueryWorkspaceResponse> {
  return requestJson<QueryWorkspaceResponse>(`/api/workspaces/${workspaceId}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listDocuments(
  params: ListDocumentsParams = {}
): Promise<DocumentsListResponse> {
  const query = buildDocumentsQuery(params);

  return requestJson<DocumentsListResponse>(
    `/api/documents${query ? `?${query}` : ""}`,
    {
      method: "GET",
    }
  );
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  return requestJson<DocumentDetail>(`/api/documents/${documentId}`, {
    method: "GET",
  });
}

export async function deleteDocument(documentId: string): Promise<void> {
  await requestJson(`/api/documents/${documentId}`, {
    method: "DELETE",
  });
}

export async function uploadDocument(
  payload: FormData
): Promise<UploadDocumentResponse> {
  return requestJson<UploadDocumentResponse>("/api/documents/upload", {
    method: "POST",
    body: payload,
  });
}

export async function reprocessDocument(
  documentId: string
): Promise<ReprocessDocumentResponse> {
  return requestJson<ReprocessDocumentResponse>(
    `/api/documents/${documentId}/reprocess`,
    {
      method: "POST",
    }
  );
}

export async function ingestText(
  payload: IngestTextReq
): Promise<IngestTextRes> {
  return requestJson<IngestTextRes>("/api/ingest/text", {
    method: "POST",
    headers: withApiKeyHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
}

export async function ingestBatch(
  payload: IngestBatchReq
): Promise<IngestBatchRes> {
  return requestJson<IngestBatchRes>("/api/ingest/batch", {
    method: "POST",
    headers: withApiKeyHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
}
