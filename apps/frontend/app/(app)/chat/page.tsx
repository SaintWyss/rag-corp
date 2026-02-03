/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/chat/page.tsx (Compat: chat global)
===============================================================================
Responsabilidades:
  - Mantener compatibilidad para la ruta histórica `/chat`.
  - Redirigir al portal principal (/workspaces) para evitar duplicación de navegación.

Colaboradores:
  - next/navigation (redirect)

Invariantes:
  - Esta ruta no debe implementar UI ni lógica de producto.
  - El acceso al chat debe ocurrir dentro del contexto de un workspace.
===============================================================================
*/

import { redirect } from "next/navigation";

/**
 * Ruta de compatibilidad: `/chat`.
 * - Decisión de producto/arquitectura: el chat vive bajo `/workspaces/[id]/chat`.
 * - Redirigimos server-side para evitar "magia" client-side dentro del AppShell.
 */
export default function ChatPage() {
  redirect("/workspaces");
}
