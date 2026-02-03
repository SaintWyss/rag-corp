/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/documents/page.tsx (Compat: documents global)
===============================================================================
Responsabilidades:
  - Mantener compatibilidad para la ruta histórica `/documents`.
  - Redirigir al portal principal (/workspaces) para evitar duplicación de navegación.

Colaboradores:
  - next/navigation (redirect)

Invariantes:
  - Esta ruta no debe implementar UI ni lógica de producto.
  - La navegación a documentos debe ocurrir dentro del contexto de un workspace.
===============================================================================
*/

import { redirect } from "next/navigation";

/**
 * Ruta de compatibilidad: `/documents`.
 * - Decisión de producto/arquitectura: documentos vive bajo `/workspaces/[id]/documents`.
 * - Redirigimos server-side para evitar duplicación de AppShell y estados inconsistentes.
 */
export default function DocumentsPage() {
  redirect("/workspaces");
}
