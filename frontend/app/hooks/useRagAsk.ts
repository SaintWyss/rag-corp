"use client";

import { askV1AskPost } from "@contracts/src/generated";
import { useCallback, useEffect, useRef, useState } from "react";

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

export function useRagAsk() {
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
        const res = await askV1AskPost(
          { query: trimmed, top_k: 3 },
          {
            headers: { "Content-Type": "application/json" },
            signal: controller.signal,
          }
        );

        clearTimeout(timeoutId);

        if (res.status === 200) {
          setState((prev) => ({
            ...prev,
            answer: res.data.answer,
            sources: res.data.sources || [],
          }));
          return;
        }

        // Handle specific HTTP error codes
        const errorMsg = getErrorMessage(res.status);
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
    [state.query]
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
