/**
===============================================================================
TARJETA CRC - apps/frontend/src/app-shell/layouts/AppMain.tsx (Layout base)
===============================================================================
Responsabilidades:
  - Proveer el contenedor semántico base para el portal autenticado.
  - Mantener el wiring sin lógica de producto ni side-effects.

Colaboradores:
  - React

Notas / Invariantes:
  - No implementa autenticación ni autorización.
  - No importa UI específica de features.
===============================================================================
*/

import type { ReactNode } from "react";

type AppMainProps = {
  children: ReactNode;
};

/**
 * Layout base del portal autenticado.
 */
export function AppMain({ children }: AppMainProps) {
  return (
    <main className="min-h-[100dvh] min-h-screen" role="main">
      {children}
    </main>
  );
}
