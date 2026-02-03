/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/not-found.tsx (404 workspace)
===============================================================================
Responsabilidades:
  - Informar cuando el workspace no existe.
  - Ofrecer un CTA para volver a workspaces.

Colaboradores:
  - next/link
===============================================================================
*/

import Link from "next/link";

export default function WorkspaceNotFound() {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-white">
      <h2 className="text-lg font-semibold">Workspace no encontrado</h2>
      <p className="mt-2 text-sm text-white/60">
        Verifica el enlace o selecciona otro workspace.
      </p>
      <Link
        href="/workspaces"
        className="mt-4 inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white/70 transition hover:border-cyan-300 hover:text-cyan-300"
      >
        Volver a workspaces
      </Link>
    </div>
  );
}
