/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/admin/users/page.tsx (Page admin users)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de usuarios admin.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/auth/AdminUsersScreen
===============================================================================
*/

import { AdminUsersScreen } from "@/features/auth/components/AdminUsersScreen";

export default function AdminUsersPage() {
  return <AdminUsersScreen />;
}
