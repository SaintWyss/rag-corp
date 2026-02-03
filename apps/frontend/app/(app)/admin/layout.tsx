/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/admin/layout.tsx (Layout admin)
===============================================================================
Responsabilidades:
  - Envolver las rutas admin con el AdminShell.
  - Dejar un punto claro para agregar el guard de rol admin.

Colaboradores:
  - shared/ui/AdminShell
===============================================================================
*/

import { AdminShell } from "@/shared/ui/AdminShell";
import type { ReactNode } from "react";

type AdminLayoutProps = {
  children: ReactNode;
};

type AdminGuardProps = {
  children: ReactNode;
};

function AdminGuard({ children }: AdminGuardProps) {
  // Punto de insercion para validar rol admin sin cambiar el wiring actual.
  return <>{children}</>;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <AdminShell>
      <AdminGuard>{children}</AdminGuard>
    </AdminShell>
  );
}
