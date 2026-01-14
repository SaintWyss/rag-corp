import type {
  IngestBatchReq,
  IngestBatchRes,
  IngestTextReq,
  IngestTextRes,
} from "@contracts/src/generated";
import { getStoredApiKey } from "./apiKey";

export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";

export type DocumentSummary = {
  id: string;
  title: string;
  source?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  file_name?: string | null;
  mime_type?: string | null;
  status?: DocumentStatus | null;
  tags?: string[];
};

export type DocumentDetail = DocumentSummary & {
  deleted_at?: string | null;
  error_message?: string | null;
};

export type DocumentsListResponse = {
  documents: DocumentSummary[];
  next_cursor?: string | null;
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

export type UploadDocumentResponse = {
  document_id: string;
  status: DocumentStatus;
  file_name: string;
  mime_type: string;
};

export type ReprocessDocumentResponse = {
  document_id: string;
  status: DocumentStatus;
  enqueued: boolean;
};

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

export async function listDocuments(
  params: ListDocumentsParams = {}
): Promise<DocumentsListResponse> {
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
  const query = searchParams.toString();

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
