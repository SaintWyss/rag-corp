/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/chat/page.tsx (Page chat workspace)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de chat con workspace.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/chat/ChatScreen
===============================================================================
*/

import { ChatScreen } from "@/features/chat/components/ChatScreen";

type PageProps = {
  params: {
    id: string;
  };
};

export default function WorkspaceChatPage({ params }: PageProps) {
  return <ChatScreen workspaceId={params.id} />;
}
