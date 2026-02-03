/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/page.tsx (Page workspaces)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de workspaces (listado/selección).
  - Mantener el wiring sin lógica de producto (sin fetch, sin side-effects).

Colaboradores:
  - features/workspaces/components/WorkspacesScreen

Invariantes:
  - El "chrome" (AppShell) debe vivir en el layout del portal workspaces, no en páginas.
  - Esta página debe ser delgada: solo delega en un screen.
===============================================================================
*/

import { WorkspacesScreen } from "@/features/workspaces/components/WorkspacesScreen";

/**
 * Portal de workspaces.
 * Nota: el AppShell se aplica a nivel de layout (`/workspaces/layout.tsx`) para evitar duplicación.
 */
export default function WorkspacesPage() {
  return <WorkspacesScreen />;
}
