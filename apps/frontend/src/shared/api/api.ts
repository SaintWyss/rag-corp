/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/api.ts (API client)
===============================================================================
Responsabilidades:
  - Centralizar requests al backend con tipado y manejo de errores.
  - Proveer parseo seguro y timeout por defecto.
  - Normalizar errores RFC7807 para el UI.

Colaboradores:
  - shared/lib/apiKey
  - fetch
  - @contracts (tipos generados)

Invariantes:
  - No se hace JSON.parse ciego sin validar content-type.
  - Los errores de red y HTTP se reportan como ApiError.
===============================================================================
*/

import { getStoredApiKey } from "@/shared/lib/apiKey";
import type {
  AppInterfacesApiHttpSchemasWorkspacesWorkspaceRes,
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

export type WorkspaceSummary = AppInterfacesApiHttpSchemasWorkspacesWorkspaceRes;

export type WorkspacesListResponse = WorkspacesListRes;

export type ListWorkspacesParams = {
  ownerUserId?: string;
  includeArchived?: boolean;
};

export type CreateWorkspacePayload = CreateWorkspaceReq;

export type AdminCreateWorkspacePayload = {
  owner_user_id: string;
  name: string;
  description?: string;
};

export type ShareWorkspacePayload = {
  user_ids: string[];
};

export type ArchiveWorkspaceResponse = ArchiveWorkspaceRes;

export type QueryWorkspacePayload = QueryReq;

export type QueryWorkspaceResponse = QueryRes;

export type ApiProblem = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  [key: string]: unknown;
};

type ApiErrorOptions = {
  status: number;
  problem?: ApiProblem;
  rawBody?: string;
  requestId?: string;
};

export class ApiError extends Error {
  status: number;
  problem?: ApiProblem;
  rawBody?: string;
  requestId?: string;

  constructor(message: string, options: ApiErrorOptions) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.problem = options.problem;
    this.rawBody = options.rawBody;
    this.requestId = options.requestId;
  }
}

type RequestOptions = RequestInit & {
  timeoutMs?: number;
  includeCredentials?: boolean;
};

type ParsedBody = {
  contentType: string;
  isJson: boolean;
  json?: unknown;
  rawText?: string;
};

const DEFAULT_API_TIMEOUT_MS = parseTimeoutMs(
  process.env.NEXT_PUBLIC_API_TIMEOUT_MS ?? process.env.API_TIMEOUT_MS,
  8000
);

function parseTimeoutMs(raw: unknown, fallbackMs: number): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallbackMs;
  }
  const min = 1000;
  const max = 30000;
  return Math.min(Math.max(parsed, min), max);
}

function getRequestId(headers: Headers): string | undefined {
  return headers.get("x-request-id") ?? headers.get("traceparent") ?? undefined;
}

function withApiKeyHeaders(headers: HeadersInit = {}): Headers {
  const nextHeaders = new Headers(headers);
  const apiKey = getStoredApiKey();
  if (apiKey) {
    nextHeaders.set("X-API-Key", apiKey);
  }
  return nextHeaders;
}

function withTimeoutSignal(
  init: RequestInit,
  timeoutMs: number
): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (init.signal) {
    if (init.signal.aborted) {
      controller.abort();
    } else {
      init.signal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }
  }

  return { signal: controller.signal, clear: () => clearTimeout(timeoutId) };
}

async function parseResponseBody(response: Response): Promise<ParsedBody> {
  const contentType = response.headers.get("content-type") ?? "";
  const isJson =
    contentType.includes("application/json") ||
    contentType.includes("application/problem+json");

  const rawText = await response.text();
  if (!rawText) {
    return { contentType, isJson };
  }

  if (isJson) {
    try {
      return {
        contentType,
        isJson,
        json: JSON.parse(rawText) as unknown,
        rawText,
      };
    } catch {
      return { contentType, isJson, rawText };
    }
  }

  return { contentType, isJson, rawText };
}

function normalizeProblem(payload: unknown, status: number): ApiProblem | undefined {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }
  const problem = payload as Record<string, unknown>;
  const hasSignals =
    typeof problem.title === "string" ||
    typeof problem.detail === "string" ||
    typeof problem.type === "string";
  if (!hasSignals) {
    return undefined;
  }

  const normalized: ApiProblem = { ...problem };
  if (typeof normalized.status !== "number") {
    normalized.status = status;
  }
  return normalized;
}

function resolveErrorMessage(
  status: number,
  problem?: ApiProblem,
  payload?: unknown,
  rawText?: string
): string {
  if (problem?.detail) {
    return problem.detail;
  }
  if (problem?.title) {
    return problem.title;
  }
  if (payload && typeof payload === "object") {
    const maybe = payload as { message?: unknown; detail?: unknown };
    if (typeof maybe.detail === "string") {
      return maybe.detail;
    }
    if (typeof maybe.message === "string") {
      return maybe.message;
    }
  }
  if (rawText) {
    return rawText;
  }
  return `Solicitud fallida (status ${status})`;
}

function buildApiError(response: Response, body: ParsedBody): ApiError {
  const problem = normalizeProblem(body.json, response.status);
  const message = resolveErrorMessage(
    response.status,
    problem,
    body.json,
    body.rawText
  );
  const rawBody = body.rawText && (!body.isJson || !body.json) ? body.rawText : undefined;

  return new ApiError(message, {
    status: response.status,
    problem,
    rawBody,
    requestId: getRequestId(response.headers),
  });
}

async function requestJson<T>(
  input: RequestInfo | URL,
  init: RequestOptions = {}
): Promise<T> {
  const { timeoutMs, includeCredentials, ...fetchInit } = init;
  const { signal, clear } = withTimeoutSignal(
    fetchInit,
    parseTimeoutMs(timeoutMs, DEFAULT_API_TIMEOUT_MS)
  );

  const responseInit: RequestInit = {
    ...fetchInit,
    headers: withApiKeyHeaders(fetchInit.headers),
    credentials:
      includeCredentials === false
        ? "omit"
        : fetchInit.credentials ?? "include",
    signal,
  };

  try {
    const response = await fetch(input, responseInit);
    const body = await parseResponseBody(response);

    if (!response.ok) {
      throw buildApiError(response, body);
    }

    if (body.json !== undefined) {
      return body.json as T;
    }

    return (body.rawText ?? null) as T;
  } finally {
    clear();
  }
}

async function requestNoContent(
  input: RequestInfo | URL,
  init: RequestOptions = {}
): Promise<void> {
  const { timeoutMs, includeCredentials, ...fetchInit } = init;
  const { signal, clear } = withTimeoutSignal(
    fetchInit,
    parseTimeoutMs(timeoutMs, DEFAULT_API_TIMEOUT_MS)
  );

  const responseInit: RequestInit = {
    ...fetchInit,
    headers: withApiKeyHeaders(fetchInit.headers),
    credentials:
      includeCredentials === false
        ? "omit"
        : fetchInit.credentials ?? "include",
    signal,
  };

  try {
    const response = await fetch(input, responseInit);
    const body = await parseResponseBody(response);

    if (!response.ok) {
      throw buildApiError(response, body);
    }
  } finally {
    clear();
  }
}

async function requestFormData<T>(
  input: RequestInfo | URL,
  init: RequestOptions = {}
): Promise<T> {
  return requestJson<T>(input, init);
}

export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await requestJson<CurrentUser>("/auth/me", { method: "GET" });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return null;
    }
    throw err;
  }
}

export async function login(email: string, password: string): Promise<void> {
  try {
    await requestNoContent("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    if (err instanceof ApiError) {
      throw new Error(err.message);
    }
    throw err;
  }
}

export async function logout(): Promise<void> {
  try {
    await requestNoContent("/auth/logout", {
      method: "POST",
    });
  } catch {
    // Logout best-effort: se ignora error de red.
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

export async function adminCreateWorkspace(
  payload: AdminCreateWorkspacePayload
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>("/api/admin/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function adminListWorkspaces(
  userId: string
): Promise<WorkspacesListResponse> {
  return requestJson<WorkspacesListResponse>(
    `/api/admin/users/${userId}/workspaces`,
    {
      method: "GET",
    }
  );
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
  await requestNoContent(
    `/api/workspaces/${workspaceId}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );
}

export async function uploadWorkspaceDocument(
  workspaceId: string,
  payload: FormData
): Promise<UploadDocumentResponse> {
  return requestFormData<UploadDocumentResponse>(
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
  return requestJson<QueryWorkspaceResponse>(
    `/api/workspaces/${workspaceId}/query`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
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
  await requestNoContent(`/api/documents/${documentId}`, {
    method: "DELETE",
  });
}

export async function uploadDocument(
  payload: FormData
): Promise<UploadDocumentResponse> {
  return requestFormData<UploadDocumentResponse>("/api/documents/upload", {
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

export async function ingestText(payload: IngestTextReq): Promise<IngestTextRes> {
  return requestJson<IngestTextRes>("/api/ingest/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function ingestBatch(
  payload: IngestBatchReq
): Promise<IngestBatchRes> {
  return requestJson<IngestBatchRes>("/api/ingest/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
