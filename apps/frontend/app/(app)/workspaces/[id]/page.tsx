/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/page.tsx (Home workspace)
===============================================================================
Responsabilidades:
  - Enrutar a la screen home del workspace.
  - Delegar la UI y lógica de producto a `WorkspaceHomeScreen`.
  - Mantener el wiring sin lógica de producto (solo params -> props).

Colaboradores:
  - features/workspaces/components/WorkspaceHomeScreen
  - React

Invariantes:
  - Este archivo NO realiza fetch ni side-effects.
  - La validación del `workspaceId` se hace en el boundary `workspaces/[id]/layout.tsx`.
===============================================================================
*/

import { WorkspaceHomeScreen } from "@/features/workspaces/components/WorkspaceHomeScreen";

type PageProps = {
  params: Promise<{
    /**
     * Segmento dinámico validado previamente por el layout del workspace.
     * Se asume no vacío por contrato del boundary.
     */
    id: string;
  }>;
};

/**
 * Página "home" de un workspace.
 * - Wiring puro: transforma params en props para el screen.
 */
export default async function WorkspaceHomePage({ params }: PageProps) {
  const { id } = await params;
  return <WorkspaceHomeScreen workspaceId={id} />;
}
