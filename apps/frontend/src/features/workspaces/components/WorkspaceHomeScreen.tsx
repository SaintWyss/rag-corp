/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/workspaces/components/WorkspaceHomeScreen.tsx (Screen home workspace)
===============================================================================
Responsabilidades:
  - Presentar una vista inicial del workspace.
  - Ofrecer accesos directos a documentos y chat.
  - Mantener un layout liviano sin carga pesada de datos.

Colaboradores:
  - next/link
===============================================================================
*/

import Link from "next/link";

type WorkspaceHomeScreenProps = {
  workspaceId: string;
};

export function WorkspaceHomeScreen({ workspaceId }: WorkspaceHomeScreenProps) {
  return (
    <section className="space-y-6">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md">
        <div className="flex flex-col gap-3">
          <span className="text-xs uppercase tracking-[0.3em] text-white/40">
            Workspace
          </span>
          <h1 className="text-3xl font-semibold text-white">
            Panel de trabajo
          </h1>
          <p className="text-sm text-white/60">
            Desde aqui podes revisar documentos y continuar las conversaciones
            con contexto.
          </p>
          <div className="text-xs text-white/40 font-mono">
            ID: {workspaceId}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link
          href={`/workspaces/${workspaceId}/documents`}
          className="group rounded-3xl border border-white/10 bg-white/5 p-6 transition hover:border-cyan-400/40 hover:bg-white/10"
        >
          <h2 className="text-lg font-bold text-white group-hover:text-cyan-300">
            Sources
          </h2>
          <p className="mt-2 text-sm text-white/60">
            Subi, filtra y monitorea el estado de tus documentos.
          </p>
        </Link>
        <Link
          href={`/workspaces/${workspaceId}/chat`}
          className="group rounded-3xl border border-white/10 bg-white/5 p-6 transition hover:border-cyan-400/40 hover:bg-white/10"
        >
          <h2 className="text-lg font-bold text-white group-hover:text-cyan-300">
            Chat
          </h2>
          <p className="mt-2 text-sm text-white/60">
            Inicia una conversacion con respuestas trazables.
          </p>
        </Link>
      </div>
    </section>
  );
}
