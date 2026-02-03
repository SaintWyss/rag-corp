/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/layout.tsx (Layout base de app)
===============================================================================
Responsabilidades:
  - Proveer un contenedor neutro para las rutas del grupo (app).
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - React
===============================================================================
*/

import type { ReactNode } from "react";

type AppLayoutProps = {
  children: ReactNode;
};

export default function AppLayout({ children }: AppLayoutProps) {
  return <div className="min-h-screen">{children}</div>;
}
