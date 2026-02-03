/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/layout.tsx (Boundary workspace)
===============================================================================
Responsabilidades:
  - Validar el parametro `id` del workspace.
  - Envolver el contenido con AppShell.
  - Reservar un espacio claro para header/breadcrumbs del workspace.

Colaboradores:
  - shared/ui/AppShell
  - next/navigation
===============================================================================
*/

import { AppShell } from "@/shared/ui/AppShell";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

type WorkspaceLayoutProps = {
  children: ReactNode;
  params: {
    id?: string;
  };
};

function normalizeWorkspaceId(raw?: string): string | null {
  if (typeof raw !== "string") {
    return null;
  }
  const trimmed = raw.trim();
  return trimmed.length ? trimmed : null;
}

export default function WorkspaceLayout({ children, params }: WorkspaceLayoutProps) {
  const workspaceId = normalizeWorkspaceId(params.id);
  if (!workspaceId) {
    notFound();
  }

  return (
    <AppShell>
      <div data-workspace-id={workspaceId}>
        {/* Espacio reservado para header/breadcrumbs del workspace */}
        <div data-workspace-header="" />
        {children}
      </div>
    </AppShell>
  );
}
