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
      className="grid gap-4 rounded-3xl border border-white/10 bg-white/5 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.35)] md:grid-cols-[1fr_auto] md:items-end"
      role="search"
      aria-label="Formulario de consulta RAG"
    >
      <div className="space-y-2">
        <label htmlFor={id} className="block">
          <span className="text-xs uppercase tracking-[0.25em] text-white/50">
            Consulta
          </span>
        </label>
        <textarea
          id={id}
          className="min-h-[120px] w-full resize-none rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-base text-white shadow-inner outline-none transition focus:border-cyan-400/60 focus:ring-2 focus:ring-cyan-400/20"
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
        className="flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-6 py-4 text-sm font-semibold uppercase tracking-[0.2em] text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={loading ? "Buscando respuesta..." : "Enviar consulta"}
      >
        {loading ? "Buscando..." : "Preguntar"}
      </button>
      <div id={errorId} role="alert" aria-live="polite" className="sr-only" />
    </form>
  );
}
