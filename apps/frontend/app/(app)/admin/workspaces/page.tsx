/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/admin/workspaces/page.tsx (Page admin workspaces)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de workspaces admin.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/workspaces/AdminWorkspacesScreen
===============================================================================
*/

import { AdminWorkspacesScreen } from "@/features/workspaces/components/AdminWorkspacesScreen";

export default function AdminWorkspacesPage() {
  return <AdminWorkspacesScreen />;
}
