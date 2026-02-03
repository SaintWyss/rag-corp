/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/admin/workspaces/page.tsx (Page admin workspaces)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de administración de workspaces.
  - Mantener wiring puro (sin lógica de producto, sin fetch, sin side-effects).

Colaboradores:
  - features/workspaces/components/AdminWorkspacesScreen

Invariantes:
  - La protección del área admin (rol/permisos) se centraliza en `app/(app)/admin/layout.tsx`.
===============================================================================
*/

import { AdminWorkspacesScreen } from "@/features/workspaces/components/AdminWorkspacesScreen";

/**
 * Página admin: workspaces.
 * - Wiring puro: delega UI y lógica al screen correspondiente.
 */
export default function AdminWorkspacesPage() {
  return <AdminWorkspacesScreen />;
}
