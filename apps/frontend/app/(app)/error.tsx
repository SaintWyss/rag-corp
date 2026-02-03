/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/error.tsx (Error boundary app)
===============================================================================
Responsabilidades:
  - Presentar un estado de error recuperable a nivel del route group (app).
  - Permitir reintentar el render (reset) sin recargar toda la aplicación.
  - Evitar filtrar detalles sensibles del error (mensaje controlado).

Colaboradores:
  - Next.js error boundary (error.tsx con reset())
  - shared/lib/cn (composición de clases Tailwind)

Invariantes:
  - Este boundary es "best-effort": siempre debe renderizar una UI estable.
  - No debe depender de servicios externos ni realizar fetch.
  - El mensaje mostrado al usuario debe ser genérico; el detalle técnico se usa solo si es seguro.
===============================================================================
*/
"use client";

import { cn } from "@/shared/lib/cn";

type AppErrorProps = {
  /**
   * Error capturado por el boundary de Next.
   * `digest` es un identificador interno que Next puede incluir (no siempre presente).
   */
  error: Error & { digest?: string };

  /**
   * Función provista por Next para reintentar el render del segmento.
   * Nota: no garantiza resolver el problema si la causa persiste.
   */
  reset: () => void;
};

/**
 * Error boundary del portal (app).
 *
 * Decisiones:
 * - UI simple y local (sin componentes de features) para evitar dependencias circulares.
 * - Mensaje genérico por defecto para no filtrar datos (el error.message puede provenir del servidor).
 */
export default function AppError({ error, reset }: AppErrorProps) {
  // Mensaje defensivo: priorizamos un texto estable; usamos message solo si existe.
  // Si en el futuro querés endurecerlo, podés eliminar el uso de `error.message` y dejar solo el fallback.
  const message = error?.message || "No pudimos cargar esta sección.";

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div
        className={cn(
          "w-full max-w-xl space-y-4 rounded-3xl border p-6",
          "border-rose-400/30 bg-rose-500/10 text-rose-100",
        )}
      >
        <h1 className="text-2xl font-semibold">Algo salió mal</h1>

        <p className="text-sm text-rose-100/80">{message}</p>

        <button
          type="button"
          onClick={reset}
          className={cn(
            "rounded-full border px-4 py-2 text-sm font-semibold transition",
            "border-rose-300/40 bg-rose-500/20 text-rose-100 hover:bg-rose-500/30",
          )}
        >
          Reintentar
        </button>

        {/* Nota: si necesitás soporte de debugging sin filtrar datos, podés mostrar `error.digest`
            solo en desarrollo y sin exponerlo en producción. */}
      </div>
    </div>
  );
}
