/**
 * @fileoverview
 * Name: useRagAsk Hook
 *
 * Responsibilities:
 *   - Manage RAG ask query state (query, answer, sources, loading, error)
 *   - Handle API call to backend workspace-scoped endpoint
 *   - Provide abort capability for pending requests
 *   - Map HTTP error codes to user-friendly messages (es-AR)
 *   - Cleanup resources on component unmount
 *
 * Collaborators:
 *   - @contracts/src/generated: Orval-generated API client
 *   - QueryForm: consumes setQuery and submit
 *   - AnswerCard: consumes answer
 *   - SourcesList: consumes sources
 *
 * Constraints:
 *   - Timeout: 30 seconds max per request
 *   - Only one request in flight at a time
 *   - Must abort pending request on unmount
 *
 * Notes:
 *   - AbortController for request cancellation
 *   - State reset on new submit
 *   - Error messages localized to Spanish
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getStoredApiKey } from "@/shared/lib/apiKey";

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

/**
 * Get user-friendly error message based on HTTP status code.
 */
function getErrorMessage(status: number): string {
  switch (status) {
    case 401:
      return "API key requerida. Configura tu clave de acceso.";
    case 403:
      return "Sin permisos para esta operación.";
    case 422:
      return "Datos inválidos. Revisa tu consulta.";
    case 429:
      return "Demasiadas solicitudes. Espera unos segundos e intenta de nuevo.";
    case 503:
      return "Servicio no disponible. Intenta de nuevo en unos minutos.";
    case 500:
    default:
      return `Error del servidor (${status}). Intenta de nuevo.`;
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

      setState((prev) => ({
        ...prev,
        loading: true,
        error: "",
        answer: "",
        sources: [],
      }));

      try {
        const apiKey = getStoredApiKey();
        const response = await fetch(`/api/workspaces/${workspaceId}/ask`, {
          method: "POST",
          headers: apiKey
            ? { "Content-Type": "application/json", "X-API-Key": apiKey }
            : { "Content-Type": "application/json" },
          body: JSON.stringify({ query: trimmed, top_k: 3 }),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        const body = await response.text();
        const data = body ? (JSON.parse(body) as { answer?: string; sources?: string[] }) : null;

        if (response.ok) {
          setState((prev) => ({
            ...prev,
            answer: data?.answer ?? "",
            sources: data?.sources ?? [],
          }));
          return;
        }

        // Handle specific HTTP error codes
        const errorMsg = getErrorMessage(response.status);
        setState((prev) => ({
          ...prev,
          error: errorMsg,
        }));
      } catch (err) {
        clearTimeout(timeoutId);

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
          error: "Error de conexión. Verifica el backend.",
        }));
      } finally {
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
