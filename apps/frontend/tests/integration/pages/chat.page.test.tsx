/**
===============================================================================
TARJETA CRC - apps/frontend/tests/integration/pages/chat.page.test.tsx
===============================================================================
Responsabilidades:
  - Validar render básico de la página de chat.
  - Confirmar presencia de header e input.

Colaboradores:
  - app/(app)/workspaces/[id]/chat/page
  - features/rag (mock)

Invariantes:
  - Sin llamadas reales a backend.
===============================================================================
*/

import { render, screen } from "@testing-library/react";

import ChatPage from "../../../app/(app)/workspaces/[id]/chat/page";

jest.mock("@/shared/api/api", () => ({
  listWorkspaces: jest.fn().mockResolvedValue({ workspaces: [] }),
}));

jest.mock("@/features/rag", () => ({
  useRagChat: () => ({
    messages: [],
    input: "",
    loading: false,
    error: "",
    conversationId: null,
    setInput: jest.fn(),
    sendMessage: jest.fn(),
    cancel: jest.fn(),
    retryLast: jest.fn(),
    reset: jest.fn(),
  }),
}));

describe("Chat Page", () => {
  it("renders the chat header", async () => {
    render(await ChatPage({ params: Promise.resolve({ id: "workspace-1" }) }));
    expect(screen.getByText(/chat con streaming/i)).toBeInTheDocument();
  });

  it("renders the message input", async () => {
    render(await ChatPage({ params: Promise.resolve({ id: "workspace-1" }) }));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });
});
