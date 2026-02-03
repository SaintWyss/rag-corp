/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/page.tsx (Home workspace)
===============================================================================
Responsabilidades:
  - Enrutar a la screen home del workspace.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/workspaces/WorkspaceHomeScreen
===============================================================================
*/

import { WorkspaceHomeScreen } from "@/features/workspaces/components/WorkspaceHomeScreen";

type PageProps = {
  params: {
    id: string;
  };
};

export default function WorkspaceHomePage({ params }: PageProps) {
  return <WorkspaceHomeScreen workspaceId={params.id} />;
}
