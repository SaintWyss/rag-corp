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

import {
  type ArchiveWorkspaceRes,
  type CreateWorkspaceReq,
  type DocumentDetailRes,
  type DocumentsListRes,
  type DocumentSummaryRes,
  type IngestBatchReq,
  type IngestBatchRes,
  type IngestTextReq,
  type IngestTextRes,
  type QueryReq,
  type QueryRes,
  type ReprocessDocumentRes,
  type UploadDocumentRes,
  type WorkspaceACL,
} from "@contracts/src/generated";

import { type ApiProblem, normalizeProblem } from "@/shared/api/contracts/problem";
import { type WorkspaceVisibility } from "@/shared/api/contracts/workspaces";
import { apiRoutes } from "@/shared/api/routes";
import { env } from "@/shared/config/env";
import { getStoredApiKey } from "@/shared/lib/apiKey";

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

export type WorkspaceSummary = {
  id: string;
  name: string;
  visibility: WorkspaceVisibility;
  owner_user_id?: string | null;
  description?: string | null;
  acl?: WorkspaceACL;
  created_at?: string | null;
  updated_at?: string | null;
  archived_at?: string | null;
};

export type AdminWorkspaceSummary = WorkspaceSummary;

export type WorkspacesListResponse = {
  workspaces: WorkspaceSummary[];
};

export type AdminWorkspacesListResponse = {
  workspaces: AdminWorkspaceSummary[];
};

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
  retries?: number;
};

type ParsedBody = {
  contentType: string;
  isJson: boolean;
  json?: unknown;
  rawText?: string;
};

const DEFAULT_API_TIMEOUT_MS = parseTimeoutMs(env.apiTimeoutMs, 8000);
const DEFAULT_GET_RETRIES = 2;
const RETRYABLE_STATUS = new Set([502, 503, 504]);

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

function backoffMs(attempt: number): number {
  const base = 200;
  return Math.min(1000, base * 2 ** attempt);
}

function shouldRetryRequest(
  method: string,
  err: unknown,
  attempt: number,
  maxRetries: number,
  signal?: AbortSignal
): boolean {
  if (method !== "GET") {
    return false;
  }
  if (attempt >= maxRetries) {
    return false;
  }
  if (signal?.aborted) {
    return false;
  }
  if (err instanceof ApiError) {
    return RETRYABLE_STATUS.has(err.status);
  }
  if (err instanceof Error && err.name === "AbortError") {
    return false;
  }
  // Network errors and unknown failures are retryable for GET.
  return true;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function requestJsonOnce<T>(
  input: RequestInfo | URL,
  init: RequestOptions = {}
): Promise<T> {
  const { timeoutMs, includeCredentials, retries: _retries, ...fetchInit } =
    init;
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

async function requestJson<T>(
  input: RequestInfo | URL,
  init: RequestOptions = {}
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const maxRetries =
    typeof init.retries === "number"
      ? Math.max(0, init.retries)
      : method === "GET"
        ? DEFAULT_GET_RETRIES
        : 0;

  let attempt = 0;
  while (true) {
    try {
      return await requestJsonOnce<T>(input, init);
    } catch (err) {
      if (
        !shouldRetryRequest(
          method,
          err,
          attempt,
          maxRetries,
          init.signal ?? undefined
        )
      ) {
        throw err;
      }
      await sleep(backoffMs(attempt));
      attempt += 1;
    }
  }
}

async function requestNoContent(
  input: RequestInfo | URL,
  init: RequestOptions = {}
): Promise<void> {
  const { timeoutMs, includeCredentials, retries: _retries, ...fetchInit } =
    init;
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
    return await requestJson<CurrentUser>(apiRoutes.auth.me, { method: "GET" });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return null;
    }
    throw err;
  }
}

export async function login(email: string, password: string): Promise<void> {
  try {
    await requestNoContent(apiRoutes.auth.login, {
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
    await requestNoContent(apiRoutes.auth.logout, {
      method: "POST",
    });
  } catch {
    // Logout best-effort: se ignora error de red.
  }
}

export async function listUsers(): Promise<UsersListResponse> {
  const data = await requestJson<UsersListResponse | AdminUser[]>(
    apiRoutes.auth.users,
    { method: "GET" }
  );
  // Compat: el backend puede devolver lista directa en vez de { users }.
  if (Array.isArray(data)) {
    return { users: data };
  }
  if (Array.isArray(data.users)) {
    return data;
  }
  return { users: [] };
}

export async function createUser(
  payload: CreateUserPayload
): Promise<AdminUser> {
  return requestJson<AdminUser>(apiRoutes.auth.users, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function disableUser(userId: string): Promise<AdminUser> {
  return requestJson<AdminUser>(apiRoutes.auth.disableUser(userId), {
    method: "POST",
  });
}

export async function resetUserPassword(
  userId: string,
  password: string
): Promise<AdminUser> {
  return requestJson<AdminUser>(apiRoutes.auth.resetPassword(userId), {
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
    `${apiRoutes.workspaces.list}${query ? `?${query}` : ""}`,
    {
      method: "GET",
    }
  );
}

export async function createWorkspace(
  payload: CreateWorkspacePayload
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>(apiRoutes.workspaces.create, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function adminCreateWorkspace(
  payload: AdminCreateWorkspacePayload
): Promise<AdminWorkspaceSummary> {
  return requestJson<AdminWorkspaceSummary>(apiRoutes.admin.workspaces, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function adminListWorkspaces(
  userId: string
): Promise<AdminWorkspacesListResponse> {
  return requestJson<AdminWorkspacesListResponse>(
    apiRoutes.admin.userWorkspaces(userId),
    {
      method: "GET",
    }
  );
}

export async function publishWorkspace(
  workspaceId: string
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>(apiRoutes.workspaces.publish(workspaceId), {
    method: "POST",
  });
}

export async function shareWorkspace(
  workspaceId: string,
  payload: ShareWorkspacePayload
): Promise<WorkspaceSummary> {
  return requestJson<WorkspaceSummary>(apiRoutes.workspaces.share(workspaceId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function archiveWorkspace(
  workspaceId: string
): Promise<ArchiveWorkspaceResponse> {
  return requestJson<ArchiveWorkspaceResponse>(
    apiRoutes.workspaces.archive(workspaceId),
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
    `${apiRoutes.workspaces.documents(workspaceId)}${query ? `?${query}` : ""}`,
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
    apiRoutes.workspaces.document(workspaceId, documentId),
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
    apiRoutes.workspaces.document(workspaceId, documentId),
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
    apiRoutes.workspaces.uploadDocument(workspaceId),
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
    apiRoutes.workspaces.reprocessDocument(workspaceId, documentId),
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
    apiRoutes.workspaces.query(workspaceId),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function ingestWorkspaceText(
  workspaceId: string,
  payload: IngestTextReq
): Promise<IngestTextRes> {
  return requestJson<IngestTextRes>(apiRoutes.workspaces.ingestText(workspaceId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function ingestWorkspaceBatch(
  workspaceId: string,
  payload: IngestBatchReq
): Promise<IngestBatchRes> {
  return requestJson<IngestBatchRes>(
    apiRoutes.workspaces.ingestBatch(workspaceId),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}
