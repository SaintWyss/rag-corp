/**
===============================================================================
TARJETA CRC - apps/frontend/src/app-shell/providers/AppProviders.tsx (Providers)
===============================================================================
Responsabilidades:
  - Centralizar providers del frontend (si aplica en el futuro).
  - Exponer un contenedor estable para el App Router.

Colaboradores:
  - React

Notas / Invariantes:
  - Pass-through por defecto: no agrega lógica ni side-effects.
===============================================================================
*/

import type { ReactNode } from "react";

type AppProvidersProps = {
  children: ReactNode;
};

/**
 * Wrapper de providers (placeholder).
 */
export function AppProviders({ children }: AppProvidersProps) {
  return <>{children}</>;
}
