/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/loading.tsx (Carga workspace)
===============================================================================
Responsabilidades:
  - Mostrar un estado de carga liviano para el workspace.

Colaboradores:
  - Ninguno
===============================================================================
*/

export default function WorkspaceLoading() {
  return (
    <div className="space-y-4">
      <div className="h-6 w-48 animate-pulse rounded-full bg-white/10" />
      <div className="h-32 w-full animate-pulse rounded-3xl bg-white/5" />
      <div className="h-24 w-full animate-pulse rounded-3xl bg-white/5" />
    </div>
  );
}
