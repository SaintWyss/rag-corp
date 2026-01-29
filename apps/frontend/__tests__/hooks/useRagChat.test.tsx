import { act, renderHook } from "@testing-library/react";
import { TextDecoder, TextEncoder } from "util";

const globalWithText = global as typeof globalThis;
globalWithText.TextEncoder =
    TextEncoder as unknown as typeof globalThis.TextEncoder;
globalWithText.TextDecoder =
    TextDecoder as unknown as typeof globalThis.TextDecoder;
import { useRagChat } from "../../src/features/rag/useRagChat";

describe("useRagChat Hook", () => {
    const mockFetch = global.fetch as jest.Mock;

    beforeEach(() => {
        mockFetch.mockReset();
    });

    it("returns initial state", () => {
        const { result } = renderHook(() => useRagChat());

        expect(result.current.messages).toEqual([]);
        expect(result.current.input).toBe("");
        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBe("");
        expect(result.current.conversationId).toBeNull();
    });

    it("shows error for empty message", async () => {
        const { result } = renderHook(() => useRagChat());

        await act(async () => {
            await result.current.sendMessage("   ");
        });

        expect(result.current.error).toBe("Escribi una pregunta antes de enviar.");
    });

    it("streams tokens and updates conversation state", async () => {
        const encoder = new TextEncoder();
        const chunks = [
            'event: sources\ndata: {"sources":[{"chunk_id":"c1","content":"Doc 1"}],"conversation_id":"conv-1"}\n\n',
            'event: token\ndata: {"token":"Hola"}\n\n',
            'event: token\ndata: {"token":" mundo"}\n\n',
            'event: done\ndata: {"answer":"Hola mundo","conversation_id":"conv-1"}\n\n',
        ];
        let readIndex = 0;

        const reader = {
            read: jest.fn().mockImplementation(() => {
                if (readIndex >= chunks.length) {
                    return Promise.resolve({ value: undefined, done: true });
                }
                const value = encoder.encode(chunks[readIndex++]);
                return Promise.resolve({ value, done: false });
            }),
        };

        mockFetch.mockResolvedValueOnce({
            ok: true,
            status: 200,
            body: { getReader: () => reader },
        });

        const { result } = renderHook(() => useRagChat());

        await act(async () => {
            await result.current.sendMessage("Hola");
        });

        const [user, assistant] = result.current.messages;
        expect(user.role).toBe("user");
        expect(user.content).toBe("Hola");
        expect(assistant.role).toBe("assistant");
        expect(assistant.content).toBe("Hola mundo");
        expect(assistant.sources).toEqual([{ chunk_id: "c1", content: "Doc 1" }]);
        expect(result.current.conversationId).toBe("conv-1");
        expect(result.current.loading).toBe(false);
    });
});
