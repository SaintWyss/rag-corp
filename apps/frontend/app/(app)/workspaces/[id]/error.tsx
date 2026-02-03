/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/error.tsx (Error workspace)
===============================================================================
Responsabilidades:
  - Presentar un estado de error recuperable dentro del contexto `workspaces/[id]`.
  - Permitir reintentar el render del segmento (reset) sin recargar toda la app.
  - Mantener una UI estable y local (sin dependencias de features).

Colaboradores:
  - Next.js error boundary (error.tsx con reset())

Invariantes:
  - No debe hacer fetch ni depender de estado global.
  - Debe ser robusto ante errores sin message.
  - El mensaje por defecto debe ser genérico para evitar filtrar detalles sensibles.
===============================================================================
*/
"use client";

type WorkspaceErrorProps = {
  /**
   * Error capturado por el boundary de Next.
   * `digest` puede estar presente como identificador interno.
   */
  error: Error & { digest?: string };

  /**
   * Función provista por Next para reintentar el render del segmento.
   */
  reset: () => void;
};

/**
 * Error boundary del segmento `workspaces/[id]`.
 * - UI simple y "best-effort": debe renderizar incluso si el error es inesperado.
 */
export default function WorkspaceError({ error, reset }: WorkspaceErrorProps) {
  // Mensaje defensivo: priorizamos un texto estable.
  const message = error?.message || "Intentá nuevamente en unos segundos.";

  return (
    <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-6 text-rose-100">
      <h2 className="text-lg font-semibold">No pudimos cargar el workspace</h2>

      <p className="mt-2 text-sm text-rose-100/80">{message}</p>

      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-full border border-rose-300/40 bg-rose-500/20 px-4 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/30"
      >
        Reintentar
      </button>

      {/* Nota: si querés debugging sin filtrar datos, mostrar `error.digest` solo en development. */}
    </div>
  );
}
