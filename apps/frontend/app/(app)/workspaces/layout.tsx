/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/layout.tsx (Layout portal workspaces)
===============================================================================
Responsabilidades:
  - Definir el "chrome" del portal de workspaces (AppShell) para todas las rutas /workspaces/**.
  - Centralizar el shell a nivel de layout para evitar duplicación en pages/segments.
  - Mantener wiring puro (sin lógica de producto, sin fetch, sin side-effects).

Colaboradores:
  - shared/ui/AppShell
  - React

Invariantes:
  - Este layout NO valida permisos ni realiza llamadas a backend.
  - Las páginas bajo /workspaces/** no deben envolver con AppShell (lo provee este layout).
===============================================================================
*/

import type { ReactNode } from "react";

import { AppShell } from "@/shared/ui/AppShell";

type WorkspacesLayoutProps = {
  /**
   * Contenido renderizado por las rutas hijas de /workspaces/**.
   */
  children: ReactNode;
};

/**
 * Layout del portal /workspaces.
 * - Aplica AppShell una sola vez para toda la sección.
 */
export default function WorkspacesLayout({ children }: WorkspacesLayoutProps) {
  return <AppShell>{children}</AppShell>;
}
