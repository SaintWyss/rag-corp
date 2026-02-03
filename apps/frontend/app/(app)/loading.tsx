/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/loading.tsx (Carga global app)
===============================================================================
Responsabilidades:
  - Mostrar un estado de carga liviano mientras hidrata la app.

Colaboradores:
  - Ninguno
===============================================================================
*/

export default function AppLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="w-full max-w-3xl space-y-4">
        <div className="h-6 w-40 animate-pulse rounded-full bg-white/10" />
        <div className="h-10 w-3/4 animate-pulse rounded-2xl bg-white/5" />
        <div className="h-32 w-full animate-pulse rounded-3xl bg-white/5" />
      </div>
    </div>
  );
}
