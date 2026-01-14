import {
  ingestBatchV1IngestBatchPost,
  ingestTextV1IngestTextPost,
  type IngestBatchReq,
  type IngestBatchRes,
  type IngestTextReq,
  type IngestTextRes,
} from "@contracts/src/generated";
import { getStoredApiKey } from "./apiKey";

export type DocumentSummary = {
  id: string;
  title: string;
  source?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string | null;
};

export type DocumentDetail = DocumentSummary & {
  deleted_at?: string | null;
};

export type DocumentsListResponse = {
  documents: DocumentSummary[];
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

export async function listDocuments(): Promise<DocumentsListResponse> {
  return requestJson<DocumentsListResponse>("/v1/documents", {
    method: "GET",
  });
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  return requestJson<DocumentDetail>(`/v1/documents/${documentId}`, {
    method: "GET",
  });
}

export async function deleteDocument(documentId: string): Promise<void> {
  await requestJson(`/v1/documents/${documentId}`, {
    method: "DELETE",
  });
}

export async function ingestText(
  payload: IngestTextReq
): Promise<IngestTextRes> {
  const res = await ingestTextV1IngestTextPost(payload, {
    headers: withApiKeyHeaders({ "Content-Type": "application/json" }),
  });
  if (res.status !== 200) {
    const message =
      (res.data as { detail?: string })?.detail ||
      `Request failed with status ${res.status}`;
    throw { status: res.status, message } satisfies ApiError;
  }
  return res.data as IngestTextRes;
}

export async function ingestBatch(
  payload: IngestBatchReq
): Promise<IngestBatchRes> {
  const res = await ingestBatchV1IngestBatchPost(payload, {
    headers: withApiKeyHeaders({ "Content-Type": "application/json" }),
  });
  if (res.status !== 200) {
    const message =
      (res.data as { detail?: string })?.detail ||
      `Request failed with status ${res.status}`;
    throw { status: res.status, message } satisfies ApiError;
  }
  return res.data as IngestBatchRes;
}
