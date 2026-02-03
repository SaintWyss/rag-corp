/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/loading.tsx (Carga workspace)
===============================================================================
Responsabilidades:
  - Mostrar un estado de carga liviano y estable para el segmento `workspaces/[id]`.
  - Proveer skeletons neutrales mientras el contenido del workspace se resuelve.

Colaboradores:
  - Ninguno

Invariantes:
  - No debe hacer fetch ni depender de estado.
  - Debe ser rápido de renderizar (markup simple + clases).
  - Debe ser reusable para distintas sub-rutas del workspace (home/chat/documents).
===============================================================================
*/

export default function WorkspaceLoading() {
  return (
    <div className="space-y-4">
      {/* Skeleton header: simula título/breadcrumbs del workspace */}
      <div
        className="h-6 w-48 animate-pulse rounded-full bg-white/10"
        aria-hidden="true"
      />

      {/* Skeleton primary content */}
      <div
        className="h-32 w-full animate-pulse rounded-3xl bg-white/5"
        aria-hidden="true"
      />

      {/* Skeleton secondary content */}
      <div
        className="h-24 w-full animate-pulse rounded-3xl bg-white/5"
        aria-hidden="true"
      />
    </div>
  );
}
