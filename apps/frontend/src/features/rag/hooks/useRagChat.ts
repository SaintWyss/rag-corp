/**
 * @fileoverview
 * Name: useRagChat Hook
 *
 * Responsibilities:
 *   - Manage chat messages and streaming state
 *   - Handle SSE streaming via /api/workspaces/{id}/ask/stream
 *   - Maintain conversation_id across turns
 *   - Support cancel and retry flows
 */
"use client";

import { getWorkspaceDocument, queryWorkspace } from "@/shared/api/api";
import { apiRoutes } from "@/shared/api/routes";
import { parseSseEvent } from "@/shared/api/sse";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import {
  networkErrorMessage,
  statusToUserMessage,
} from "@/shared/lib/httpErrors";
import { useCallback, useEffect, useRef, useState } from "react";

type ChatRole = "user" | "assistant";
type MessageStatus = "streaming" | "complete" | "error" | "cancelled";

type AbortReason = "cancel" | "timeout" | "overflow" | null;

export type StreamSource = {
  chunk_id: string;
  content: string;
};

export type VerifiedSource = {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
  document_title?: string | null;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  status?: MessageStatus;
  sources?: StreamSource[];
  verifiedSources?: VerifiedSource[];
};

type ChatState = {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  error: string;
  conversationId: string | null;
};

const initialState: ChatState = {
  messages: [],
  input: "",
  loading: false,
  error: "",
  conversationId: null,
};

const STREAM_TIMEOUT_MS = 30_000;
const MAX_STREAM_EVENTS = 2000;
const MAX_STREAM_CHARS = 12000;

function createMessageId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function safeJsonParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

type UseRagChatOptions = {
  workspaceId: string;
};

export function useRagChat({ workspaceId }: UseRagChatOptions) {
  const [state, setState] = useState<ChatState>(initialState);
  const abortControllerRef = useRef<AbortController | null>(null);
  const abortReasonRef = useRef<AbortReason>(null);
  const lastUserMessageRef = useRef<string | null>(null);
  const titleCacheRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const setInput = useCallback((value: string) => {
    setState((prev) => ({ ...prev, input: value }));
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
    lastUserMessageRef.current = null;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortReasonRef.current = "cancel";
      abortControllerRef.current.abort();
    }
  }, []);

  const loadDocumentTitles = useCallback(
    async (documentIds: string[]): Promise<Map<string, string>> => {
      const titleMap = titleCacheRef.current;
      const missing = documentIds.filter((id) => !titleMap.has(id));

      await Promise.all(
        missing.map(async (documentId) => {
          try {
            const doc = await getWorkspaceDocument(workspaceId, documentId);
            titleMap.set(documentId, doc.title);
          } catch {
            // Ignore missing titles for best-effort verification.
          }
        })
      );

      return titleMap;
    },
    [workspaceId]
  );

  const sendMessage = useCallback(
    async (messageText: string) => {
      const trimmed = messageText.trim();
      if (!trimmed) {
        setState((prev) => ({
          ...prev,
          error: "Escribi una pregunta antes de enviar.",
        }));
        return;
      }

      if (!workspaceId) {
        setState((prev) => ({
          ...prev,
          error: "Selecciona un workspace antes de preguntar.",
        }));
        return;
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const userMessage: ChatMessage = {
        id: createMessageId(),
        role: "user",
        content: trimmed,
      };
      const assistantId = createMessageId();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "streaming",
      };

      lastUserMessageRef.current = trimmed;
      abortReasonRef.current = null;

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage, assistantMessage],
        loading: true,
        error: "",
        input: "",
      }));

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const timeoutId = setTimeout(() => {
        abortReasonRef.current = "timeout";
        controller.abort();
      }, STREAM_TIMEOUT_MS);

      const topK = 3;
      const payload: Record<string, unknown> = {
        query: trimmed,
        top_k: topK,
      };
      if (state.conversationId) {
        payload.conversation_id = state.conversationId;
      }

      void (async () => {
        try {
          const result = await queryWorkspace(workspaceId, {
            query: trimmed,
            top_k: topK,
          });
          const uniqueIds = Array.from(
            new Set(result.matches.map((match) => match.document_id))
          );
          const titles = await loadDocumentTitles(uniqueIds);
          const verifiedSources: VerifiedSource[] = result.matches.map(
            (match) => ({
              ...match,
              document_title: titles.get(match.document_id) ?? null,
            })
          );
          setState((prev) => ({
            ...prev,
            messages: prev.messages.map((msg) =>
              msg.id === assistantId ? { ...msg, verifiedSources } : msg
            ),
          }));
        } catch {
          // Best-effort verification; don't interrupt chat flow.
        }
      })();

      try {
        const apiKey = getStoredApiKey();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (apiKey) {
          headers["X-API-Key"] = apiKey;
        }

        const response = await fetch(
          apiRoutes.workspaces.askStream(workspaceId),
          {
            method: "POST",
            headers,
            body: JSON.stringify(payload),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: statusToUserMessage(response.status),
            messages: prev.messages.map((msg) =>
              msg.id === assistantId
                ? { ...msg, status: "error" }
                : msg
            ),
          }));
          return;
        }

        if (!response.body) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: "Respuesta vacia del servidor.",
          }));
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let totalChars = 0;
        let eventCount = 0;

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          totalChars += chunk.length;
          if (totalChars > MAX_STREAM_CHARS) {
            abortReasonRef.current = "overflow";
            controller.abort();
            break;
          }

          buffer += chunk;

          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const parsed = parseSseEvent(part);
            if (!parsed) {
              continue;
            }

            eventCount += 1;
            if (eventCount > MAX_STREAM_EVENTS) {
              abortReasonRef.current = "overflow";
              controller.abort();
              break;
            }

            if (parsed.event === "token") {
              const data = safeJsonParse<{ token?: string }>(parsed.data);
              if (data?.token) {
                setState((prev) => ({
                  ...prev,
                  messages: prev.messages.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: msg.content + data.token }
                      : msg
                  ),
                }));
              }
            }

            if (parsed.event === "sources") {
              const data = safeJsonParse<{
                sources?: StreamSource[];
                conversation_id?: string | null;
              }>(parsed.data);
              if (!data) {
                continue;
              }
              setState((prev) => ({
                ...prev,
                conversationId: data.conversation_id ?? prev.conversationId,
                messages: prev.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, sources: data.sources ?? [] }
                    : msg
                ),
              }));
            }

            if (parsed.event === "done") {
              const data = safeJsonParse<{
                answer?: string;
                conversation_id?: string | null;
              }>(parsed.data);
              if (!data) {
                continue;
              }
              setState((prev) => ({
                ...prev,
                loading: false,
                conversationId: data.conversation_id ?? prev.conversationId,
                messages: prev.messages.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        content: data.answer ?? msg.content,
                        status: "complete",
                      }
                    : msg
                ),
              }));
            }

            if (parsed.event === "error") {
              const data = safeJsonParse<{ error?: string }>(parsed.data);
              setState((prev) => ({
                ...prev,
                loading: false,
                error: data?.error || "Error en el streaming.",
                messages: prev.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, status: "error" }
                    : msg
                ),
              }));
            }
          }

          if (abortReasonRef.current === "overflow") {
            break;
          }
        }

        if (abortReasonRef.current) {
          const abortError = new Error("Stream aborted");
          abortError.name = "AbortError";
          throw abortError;
        }

        setState((prev) => ({
          ...prev,
          loading: false,
          messages: prev.messages.map((msg) =>
            msg.id === assistantId && msg.status === "streaming"
              ? { ...msg, status: "complete" }
              : msg
          ),
        }));
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          const reason = abortReasonRef.current as AbortReason;
          const message =
            reason === "timeout"
              ? "Tiempo de espera agotado."
              : reason === "overflow"
                ? "Respuesta demasiado grande."
                : "Solicitud cancelada.";

          setState((prev) => ({
            ...prev,
            loading: false,
            error: message,
            messages: prev.messages.map((msg) => {
              if (msg.id !== assistantId) {
                return msg;
              }
              return {
                ...msg,
                status: reason === "cancel" ? "cancelled" : "error",
              };
            }),
          }));
          return;
        }

        console.error(err);
        setState((prev) => ({
          ...prev,
          loading: false,
          error: networkErrorMessage(),
          messages: prev.messages.map((msg) =>
            msg.id === assistantId ? { ...msg, status: "error" } : msg
          ),
        }));
      } finally {
        clearTimeout(timeoutId);
      }
    },
    [loadDocumentTitles, state.conversationId, workspaceId]
  );

  const retryLast = useCallback(async () => {
    if (!lastUserMessageRef.current) {
      return;
    }
    await sendMessage(lastUserMessageRef.current);
  }, [sendMessage]);

  return {
    messages: state.messages,
    input: state.input,
    loading: state.loading,
    error: state.error,
    conversationId: state.conversationId,
    setInput,
    sendMessage,
    cancel,
    retryLast,
    reset,
  };
}
