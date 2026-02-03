/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/error.tsx (Error workspace)
===============================================================================
Responsabilidades:
  - Mostrar errores recuperables en rutas de workspace.
  - Permitir reintentar con reset().

Colaboradores:
  - Next.js error boundary
===============================================================================
*/
"use client";

type WorkspaceErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function WorkspaceError({ error, reset }: WorkspaceErrorProps) {
  return (
    <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-6 text-rose-100">
      <h2 className="text-lg font-semibold">No pudimos cargar el workspace</h2>
      <p className="mt-2 text-sm text-rose-100/80">
        {error?.message || "Intenta nuevamente en unos segundos."}
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-full border border-rose-300/40 bg-rose-500/20 px-4 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/30"
      >
        Reintentar
      </button>
    </div>
  );
}
