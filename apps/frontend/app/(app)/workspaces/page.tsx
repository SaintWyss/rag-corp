/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/page.tsx (Page workspaces)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de workspaces.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/workspaces/WorkspacesScreen
  - shared/ui/AppShell
===============================================================================
*/

import { WorkspacesScreen } from "@/features/workspaces/components/WorkspacesScreen";
import { AppShell } from "@/shared/ui/AppShell";

export default function WorkspacesPage() {
  return (
    <AppShell>
      <WorkspacesScreen />
    </AppShell>
  );
}
