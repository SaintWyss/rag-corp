/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/loading.tsx (Carga global app)
===============================================================================
Responsabilidades:
  - Mostrar un estado de carga liviano mientras el route group (app) resuelve segmentos.
  - Proveer una UI estable (skeleton) sin depender de datos ni de servicios.

Colaboradores:
  - Ninguno

Invariantes:
  - No debe hacer fetch ni leer estado global.
  - Debe ser rápido de renderizar (solo markup + clases).
  - Debe ser visualmente neutro para reutilizarse en múltiples pantallas.
===============================================================================
*/

export default function AppLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="w-full max-w-3xl space-y-4">
        {/* Skeleton header: simula un título o breadcrumb */}
        <div
          className="h-6 w-40 animate-pulse rounded-full bg-white/10"
          aria-hidden="true"
        />

        {/* Skeleton primary: simula un bloque principal (input / toolbar) */}
        <div
          className="h-10 w-3/4 animate-pulse rounded-2xl bg-white/5"
          aria-hidden="true"
        />

        {/* Skeleton content: simula el cuerpo principal */}
        <div
          className="h-32 w-full animate-pulse rounded-3xl bg-white/5"
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
