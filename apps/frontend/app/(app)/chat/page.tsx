/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/chat/page.tsx (Page chat)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de chat.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/chat/ChatScreen
  - shared/ui/AppShell
===============================================================================
*/

import { ChatScreen } from "@/features/chat/components/ChatScreen";
import { AppShell } from "@/shared/ui/AppShell";

export default function ChatPage() {
  return (
    <AppShell>
      <ChatScreen />
    </AppShell>
  );
}
