/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/rag/hooks/useRagAsk.ts (Hook ask)
===============================================================================
Responsabilidades:
  - Manejar estado de pregunta/respuesta/sources del flujo ask.
  - Orquestar llamada HTTP con timeout y abort.
  - Normalizar errores hacia mensajes de UI.

Colaboradores:
  - shared/api/routes
  - shared/lib/httpErrors

Invariantes:
  - Un request en vuelo por vez.
  - Abort en unmount para evitar fugas.
===============================================================================
*/
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiRoutes } from "@/shared/api/routes";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import { networkErrorMessage, statusToUserMessage } from "@/shared/lib/httpErrors";

/** Request timeout in milliseconds (30 seconds) */
const REQUEST_TIMEOUT_MS = 30_000;

type AskState = {
  query: string;
  answer: string;
  sources: string[];
  loading: boolean;
  error: string;
};

const initialState: AskState = {
  query: "",
  answer: "",
  sources: [],
  loading: false,
  error: "",
};

type UseRagAskOptions = {
  workspaceId: string;
};

function safeJsonParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function useRagAsk({ workspaceId }: UseRagAskOptions) {
  const [state, setState] = useState<AskState>(initialState);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup: abort pending request on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const setQuery = useCallback((value: string) => {
    setState((prev) => ({ ...prev, query: value }));
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  const submit = useCallback(
    async (event?: React.FormEvent) => {
      event?.preventDefault();
      const trimmed = state.query.trim();

      if (!trimmed) {
        setState((prev) => ({
          ...prev,
          error: "Escribi una pregunta antes de enviar.",
          answer: "",
          sources: [],
        }));
        return;
      }

      if (!workspaceId) {
        setState((prev) => ({
          ...prev,
          error: "Selecciona un workspace antes de preguntar.",
          answer: "",
          sources: [],
        }));
        return;
      }

      // Abort previous request if any
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new AbortController with timeout
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
      const topK = 3;

      setState((prev) => ({
        ...prev,
        loading: true,
        error: "",
        answer: "",
        sources: [],
      }));

      try {
        const apiKey = getStoredApiKey();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (apiKey) {
          headers["X-API-Key"] = apiKey;
        }

        const response = await fetch(apiRoutes.workspaces.ask(workspaceId), {
          method: "POST",
          headers,
          body: JSON.stringify({ query: trimmed, top_k: topK }),
          signal: controller.signal,
        });

        const body = await response.text();
        const data = body
          ? safeJsonParse<{ answer?: string; sources?: string[] }>(body)
          : null;

        if (response.ok) {
          setState((prev) => ({
            ...prev,
            answer: data?.answer ?? "",
            sources: data?.sources ?? [],
          }));
          return;
        }

        // Handle specific HTTP error codes
        const errorMsg = statusToUserMessage(response.status);
        setState((prev) => ({
          ...prev,
          error: errorMsg,
        }));
      } catch (err) {
        // Handle abort/timeout
        if (err instanceof Error && err.name === "AbortError") {
          setState((prev) => ({
            ...prev,
            error: "Tiempo de espera agotado. Intenta de nuevo.",
          }));
          return;
        }

        console.error(err);
        setState((prev) => ({
          ...prev,
          error: networkErrorMessage(),
        }));
      } finally {
        clearTimeout(timeoutId);
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [state.query, workspaceId]
  );

  return {
    query: state.query,
    answer: state.answer,
    sources: state.sources,
    loading: state.loading,
    error: state.error,
    setQuery,
    submit,
    reset,
  };
}
