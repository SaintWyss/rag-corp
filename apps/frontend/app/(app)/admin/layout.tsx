/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/admin/layout.tsx (Layout admin)
===============================================================================
Responsabilidades:
  - Envolver el portal admin con `AdminShell` (chrome del área).
  - Centralizar el "boundary" del área admin para evitar duplicación en páginas.
  - Proveer un punto único y explícito para agregar el guard de rol admin.

Colaboradores:
  - shared/ui/shells/AdminShell
  - React

Invariantes:
  - Este layout no debe contener lógica de producto ni UI específica de páginas.
  - El guard de admin debe implementarse de forma server-side cuando esté disponible (evitar client-only si es posible).
===============================================================================
*/

import type { ReactNode } from "react";

import { AdminGuard } from "@/app-shell/guards/AdminGuard";
import { AdminShell } from "@/shared/ui/shells/AdminShell";

type AdminLayoutProps = {
  /**
   * Contenido renderizado por las rutas hijas del portal /admin/**.
   */
  children: ReactNode;
};

/**
 * Layout del portal admin.
 * - Aplica el shell una sola vez para toda la sección.
 */
export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <AdminShell>
      <AdminGuard>{children}</AdminGuard>
    </AdminShell>
  );
}
