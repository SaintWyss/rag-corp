/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/layout.tsx (Layout base de app)
===============================================================================
Responsabilidades:
  - Proveer un contenedor neutro y semántico para las rutas del grupo (app).
  - Mantener el wiring sin lógica de producto (sin fetch, sin guards, sin UI shell).

Colaboradores:
  - React

Invariantes:
  - Este layout NO implementa autenticación/autorización.
  - Este layout NO importa componentes de features ni de shared UI (para evitar acoplamiento).
===============================================================================
*/

import type { ReactNode } from "react";

type AppLayoutProps = {
  children: ReactNode;
};

/**
 * Layout neutro del route group (app).
 * Nota: Usamos <main> por semántica y accesibilidad; el "shell" real vive en layouts más específicos
 * (por ejemplo workspaces/ o admin/), no acá.
 */
export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <main className="min-h-[100dvh] min-h-screen" role="main">
      {children}
    </main>
  );
}
