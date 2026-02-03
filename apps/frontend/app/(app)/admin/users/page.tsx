/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/admin/users/page.tsx (Page admin users)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de administración de usuarios.
  - Mantener wiring puro (sin lógica de producto, sin fetch, sin side-effects).

Colaboradores:
  - features/auth/components/AdminUsersScreen

Invariantes:
  - La protección del área admin (rol/permisos) se centraliza en `app/(app)/admin/layout.tsx`.
===============================================================================
*/

import { AdminUsersScreen } from "@/features/auth/components/AdminUsersScreen";

/**
 * Página admin: usuarios.
 * - Wiring puro: delega UI y lógica al screen correspondiente.
 */
export default function AdminUsersPage() {
  return <AdminUsersScreen />;
}
