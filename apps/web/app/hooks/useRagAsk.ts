"use client";

import { askV1AskPost } from "@contracts/src/generated";
import { useCallback, useState } from "react";

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

export function useRagAsk() {
  const [state, setState] = useState<AskState>(initialState);

  const setQuery = useCallback((value: string) => {
    setState((prev) => ({ ...prev, query: value }));
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
          { headers: { "Content-Type": "application/json" } }
        );

        if (res.status === 200) {
          setState((prev) => ({
            ...prev,
            answer: res.data.answer,
            sources: res.data.sources || [],
          }));
          return;
        }

        setState((prev) => ({
          ...prev,
          error: `Error en el servidor: ${res.status}`,
        }));
      } catch (err) {
        console.error(err);
        setState((prev) => ({
          ...prev,
          error: "Error de conexion. Verifica el backend.",
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
  };
}
