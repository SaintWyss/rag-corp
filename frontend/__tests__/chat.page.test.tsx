import { render, screen } from "@testing-library/react";
import ChatPage from "../app/chat/page";

jest.mock("../app/hooks/useRagChat", () => ({
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
    it("renders the chat header", () => {
        render(<ChatPage />);
        expect(screen.getByText(/chat con streaming/i)).toBeInTheDocument();
    });

    it("renders the message input", () => {
        render(<ChatPage />);
        expect(screen.getByRole("textbox")).toBeInTheDocument();
    });
});
