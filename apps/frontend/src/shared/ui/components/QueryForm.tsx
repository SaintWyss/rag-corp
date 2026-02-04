/**
 * @fileoverview
 * Name: QueryForm Component
 *
 * Responsibilities:
 *   - Render textarea for user query input
 *   - Handle form submission
 *   - Show loading state on submit button
 *   - Provide accessible form controls (ARIA)
 *
 * Collaborators:
 *   - page.tsx: parent that passes props
 *   - useRagAsk: provides onQueryChange and onSubmit
 *
 * Constraints:
 *   - Must be accessible (WCAG 2.1 AA)
 *   - Textarea disabled during loading
 *   - aria-busy reflects loading state
 *
 * Notes:
 *   - Uses useId() for unique accessible IDs
 *   - role="search" for semantic HTML
 *   - Spanish placeholder text
 */
"use client";

import { useId } from "react";

type QueryFormProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  loading: boolean;
};

export function QueryForm({
  query,
  onQueryChange,
  onSubmit,
  loading,
}: QueryFormProps) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <form
      onSubmit={onSubmit}
      className="grid gap-4 rounded-3xl border border-white/40 bg-white/60 p-5 shadow-xl backdrop-blur-md md:grid-cols-[1fr_auto] md:items-end"
      role="search"
      aria-label="Formulario de consulta RAG"
    >
      <div className="space-y-2">
        <label htmlFor={id} className="block">
          <span className="text-xs uppercase tracking-[0.25em] text-slate-500 font-bold">
            Consulta
          </span>
        </label>
        <textarea
          id={id}
          className="min-h-[120px] w-full resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-base text-slate-800 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 placeholder:text-slate-400"
          placeholder="Ejemplo: Que dice el manual sobre vacaciones?"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          disabled={loading}
          aria-describedby={errorId}
          aria-busy={loading}
          aria-required="true"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-4 text-sm font-bold uppercase tracking-[0.2em] text-white transition hover:bg-indigo-500 shadow-lg shadow-indigo-600/20 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
        aria-label={loading ? "Buscando respuesta..." : "Enviar consulta"}
      >
        {loading ? "Buscando..." : "Preguntar"}
      </button>
      <div id={errorId} role="alert" aria-live="polite" className="sr-only" />
    </form>
  );
}
