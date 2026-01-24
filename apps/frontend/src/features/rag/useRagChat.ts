/**
 * @fileoverview
 * Name: useRagChat Hook
 *
 * Responsibilities:
 *   - Manage chat messages and streaming state
 *   - Handle SSE streaming via /api/ask/stream
 *   - Maintain conversation_id across turns
 *   - Support cancel and retry flows
 */
"use client";

import { getWorkspaceDocument, queryWorkspace } from "@/shared/api/api";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import { useCallback, useEffect, useRef, useState } from "react";

type ChatRole = "user" | "assistant";
type MessageStatus = "streaming" | "complete" | "error" | "cancelled";

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

function createMessageId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getErrorMessage(status: number): string {
  switch (status) {
    case 401:
      return "API key requerida. Configura tu clave de acceso.";
    case 403:
      return "Sin permisos para esta operacion.";
    case 422:
      return "Datos invalidos. Revisa tu consulta.";
    case 429:
      return "Demasiadas solicitudes. Espera unos segundos e intenta de nuevo.";
    case 503:
      return "Servicio no disponible. Intenta de nuevo en unos minutos.";
    case 500:
    default:
      return `Error del servidor (${status}). Intenta de nuevo.`;
  }
}

type SseEvent = {
  event: string;
  data: string;
};

function parseSseEvent(raw: string): SseEvent | null {
  if (!raw.trim()) {
    return null;
  }
  const lines = raw.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  return {
    event,
    data: dataLines.join("\n"),
  };
}

async function loadDocumentTitles(
  workspaceId: string,
  documentIds: string[]
): Promise<Map<string, string>> {
  const titleMap = new Map<string, string>();
  await Promise.all(
    documentIds.map(async (documentId) => {
      try {
        const doc = await getWorkspaceDocument(workspaceId, documentId);
        titleMap.set(documentId, doc.title);
      } catch {
        // Ignore missing titles for best-effort verification.
      }
    })
  );
  return titleMap;
}

type UseRagChatOptions = {
  workspaceId?: string;
};

export function useRagChat(options: UseRagChatOptions = {}) {
  const { workspaceId } = options;
  const [state, setState] = useState<ChatState>(initialState);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string | null>(null);

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
      abortControllerRef.current.abort();
    }
  }, []);

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

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage, assistantMessage],
        loading: true,
        error: "",
        input: "",
      }));

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const topK = 3;
      const payload: Record<string, unknown> = {
        query: trimmed,
        top_k: topK,
      };
      if (state.conversationId) {
        payload.conversation_id = state.conversationId;
      }

      if (workspaceId) {
        void (async () => {
          try {
            const result = await queryWorkspace(workspaceId, {
              query: trimmed,
              top_k: topK,
            });
            const uniqueIds = Array.from(
              new Set(result.matches.map((match) => match.document_id))
            );
            const titles = await loadDocumentTitles(workspaceId, uniqueIds);
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
      }

      try {
        const apiKey = getStoredApiKey();
        const streamPath = workspaceId
          ? `/api/workspaces/${workspaceId}/ask/stream`
          : "/api/ask/stream";
        const response = await fetch(streamPath, {
          method: "POST",
          headers: apiKey
            ? { "Content-Type": "application/json", "X-API-Key": apiKey }
            : { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!response.ok) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: getErrorMessage(response.status),
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

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }
          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const parsed = parseSseEvent(part);
            if (!parsed) {
              continue;
            }

            if (parsed.event === "token") {
              const data = JSON.parse(parsed.data) as { token?: string };
              if (data.token) {
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
              const data = JSON.parse(parsed.data) as {
                sources?: StreamSource[];
                conversation_id?: string | null;
              };
              setState((prev) => ({
                ...prev,
                conversationId:
                  data.conversation_id ?? prev.conversationId,
                messages: prev.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, sources: data.sources ?? [] }
                    : msg
                ),
              }));
            }

            if (parsed.event === "done") {
              const data = JSON.parse(parsed.data) as {
                answer?: string;
                conversation_id?: string | null;
              };
              setState((prev) => ({
                ...prev,
                loading: false,
                conversationId:
                  data.conversation_id ?? prev.conversationId,
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
              const data = JSON.parse(parsed.data) as { error?: string };
              setState((prev) => ({
                ...prev,
                loading: false,
                error: data.error || "Error en el streaming.",
                messages: prev.messages.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, status: "error" }
                    : msg
                ),
              }));
            }
          }
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
          setState((prev) => ({
            ...prev,
            loading: false,
            error: "Solicitud cancelada.",
            messages: prev.messages.map((msg) =>
              msg.id === assistantId
                ? { ...msg, status: "cancelled" }
                : msg
            ),
          }));
          return;
        }

        console.error(err);
        setState((prev) => ({
          ...prev,
          loading: false,
          error: "Error de conexion. Verifica el backend.",
          messages: prev.messages.map((msg) =>
            msg.id === assistantId ? { ...msg, status: "error" } : msg
          ),
        }));
      }
    },
    [state.conversationId, workspaceId]
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
