/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/page.tsx (Entrada app)
===============================================================================
Responsabilidades:
  - Redirigir al destino seguro dentro del portal.

Colaboradores:
  - next/navigation
  - shared/lib/safeNext
===============================================================================
*/

import { sanitizeNextPath } from "@/shared/lib/safeNext";
import { redirect } from "next/navigation";

type PageProps = {
  searchParams?: {
    next?: string | string[];
  };
};

export default function AppEntryPage({ searchParams }: PageProps) {
  const rawNext = Array.isArray(searchParams?.next)
    ? searchParams?.next[0]
    : searchParams?.next;
  const target = sanitizeNextPath(rawNext);
  redirect(target);
}
