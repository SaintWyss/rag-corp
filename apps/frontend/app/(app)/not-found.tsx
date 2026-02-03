/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/not-found.tsx (404 app)
===============================================================================
Responsabilidades:
  - Informar rutas no encontradas dentro del grupo (app).
  - Ofrecer un CTA para volver a workspaces.

Colaboradores:
  - next/link
===============================================================================
*/

import Link from "next/link";

export default function AppNotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="w-full max-w-xl space-y-4 rounded-3xl border border-white/10 bg-white/5 p-6 text-white">
        <h1 className="text-2xl font-semibold">Pagina no encontrada</h1>
        <p className="text-sm text-white/60">
          La ruta solicitada no existe o fue movida.
        </p>
        <Link
          href="/workspaces"
          className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white/70 transition hover:border-cyan-300 hover:text-cyan-300"
        >
          Volver a workspaces
        </Link>
      </div>
    </div>
  );
}
