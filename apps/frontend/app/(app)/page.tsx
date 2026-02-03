/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/page.tsx (Entrada app)
===============================================================================
Responsabilidades:
  - Determinar un destino de navegación seguro dentro del portal (app).
  - Redirigir de forma inmediata (server-side) para evitar renders intermedios.

Colaboradores:
  - next/navigation (redirect)
  - shared/lib/safeNext (sanitizeNextPath)

Invariantes:
  - Nunca redirige a un origen externo (same-origin only).
  - Si el parámetro `next` es inválido o no existe, usa un destino seguro por defecto.
===============================================================================
*/

import { redirect } from "next/navigation";

import { sanitizeNextPath } from "@/shared/lib/safeNext";

type AppEntrySearchParams = {
  /**
   * Destino solicitado por el usuario (puede venir como string o array por el parser de Next).
   * Ejemplos:
   *   - "/workspaces"
   *   - "/workspaces/123/documents"
   */
  next?: string | string[];
};

type PageProps = {
  /**
   * Parámetros de query del request actual (server component).
   * Nota: Next entrega `searchParams` ya parseado.
   */
  searchParams?: AppEntrySearchParams;
};

/**
 * Página de entrada del portal (app).
 *
 * Diseño:
 * - Esta página NO renderiza UI. Es un "router shim" (wiring puro).
 * - La sanitización se delega a `sanitizeNextPath` para garantizar same-origin
 *   y evitar open-redirects.
 */
export default function AppEntryPage({ searchParams }: PageProps) {
  // Normalización defensiva: Next puede entregar query params como string o string[].
  const rawNext = Array.isArray(searchParams?.next)
    ? searchParams?.next[0]
    : searchParams?.next;

  // Fallback seguro: si `next` no es válido, siempre enviamos al portal principal.
  const target = sanitizeNextPath(rawNext) || "/workspaces";

  // Redirect server-side: no deja que el cliente vea un estado intermedio.
  redirect(target);
}
