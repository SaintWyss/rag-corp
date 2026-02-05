/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/chat/page.tsx (Page chat workspace)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de chat dentro del contexto de un workspace.
  - Delegar UI y lógica de producto a `ChatScreen`.
  - Mantener wiring puro (params -> props), sin fetch ni side-effects.

Colaboradores:
  - features/chat/components/ChatScreen
  - React

Invariantes:
  - La validación del `workspaceId` se realiza en el layout `workspaces/[id]/layout.tsx`.
  - Este archivo no debe importar infraestructura (api client) ni lógica de negocio.
===============================================================================
*/

import { ChatScreen } from "@/features/chat/components/ChatScreen";

type PageProps = {
  params: Promise<{
    /**
     * Segmento dinámico validado por el boundary del workspace.
     */
    id: string;
  }>;
};

/**
 * Página de chat del workspace.
 * - Wiring puro: transforma params en props para el screen.
 */
export default async function WorkspaceChatPage({ params }: PageProps) {
  const { id } = await params;
  return <ChatScreen workspaceId={id} />;
}
