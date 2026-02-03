/**
===============================================================================
TARJETA CRC — apps/frontend/src/shared/lib/cn.ts (Classnames helper)
===============================================================================

Responsabilidades:
  - Combinar classnames condicionales.
  - Normalizar clases Tailwind (dedupe) con tailwind-merge.

Colaboradores:
  - clsx
  - tailwind-merge
===============================================================================
*/

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
