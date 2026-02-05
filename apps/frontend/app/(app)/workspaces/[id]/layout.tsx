/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/layout.tsx (Boundary workspace)
===============================================================================
Responsabilidades:
  - Validar el parámetro `id` del workspace (fail-fast).
  - Exponer un contenedor estable del contexto workspace para las rutas hijas.
  - Reservar un slot claro para header/breadcrumbs del workspace (wiring).

Colaboradores:
  - next/navigation (notFound)
  - React

Invariantes:
  - No realiza fetch ni side-effects externos.
  - No implementa lógica de producto; solo wiring + validaciones.
  - Si `id` es inválido, responde con 404 del segmento (notFound()).
  - El AppShell del portal debe aplicarse a nivel /workspaces/layout.tsx para evitar duplicación.
===============================================================================
*/

import { notFound } from "next/navigation";
import type { ReactNode } from "react";

type WorkspaceLayoutProps = {
  children: ReactNode;
  params: Promise<{ id: string }>;
};

/**
 * Normaliza el workspace id de forma defensiva.
 * - Evita strings vacíos o con solo espacios.
 * - No intenta "corregir" formatos: el contrato de id se valida en capas de dominio/servicio.
 */
function normalizeWorkspaceId(raw?: string | null): string | null {
  if (typeof raw !== "string") {
    return null;
  }
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * Layout del contexto `workspaces/[id]`.
 * - Se encarga solo del boundary (validación + contenedor).
 * - El contenido real vive en screens de `src/features/*`.
 */
export default async function WorkspaceLayout({
  children,
  params,
}: WorkspaceLayoutProps) {
  const { id } = await params;
  const workspaceId = normalizeWorkspaceId(id);

  // Fail-fast: si el id es inválido, delegamos a la página 404 del segmento.
  if (!workspaceId) {
    notFound();
  }

  return (
    <div data-workspace-id={workspaceId}>
      {/* Slot reservado para header/breadcrumbs del workspace (wiring).
          Nota: la UI real debe vivir en `src/features/workspaces/*` para evitar acoplamiento con routing. */}
      <div data-workspace-header="" />

      {children}
    </div>
  );
}
