/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/error.tsx (Error boundary app)
===============================================================================
Responsabilidades:
  - Mostrar un error recuperable a nivel de grupo (app).
  - Permitir reintentar el render con reset().

Colaboradores:
  - Next.js error boundary
===============================================================================
*/
"use client";

type AppErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function AppError({ error, reset }: AppErrorProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="w-full max-w-xl space-y-4 rounded-3xl border border-rose-400/30 bg-rose-500/10 p-6 text-rose-100">
        <h1 className="text-2xl font-semibold">Algo salio mal</h1>
        <p className="text-sm text-rose-100/80">
          {error?.message || "No pudimos cargar esta seccion."}
        </p>
        <button
          type="button"
          onClick={reset}
          className="rounded-full border border-rose-300/40 bg-rose-500/20 px-4 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/30"
        >
          Reintentar
        </button>
      </div>
    </div>
  );
}
