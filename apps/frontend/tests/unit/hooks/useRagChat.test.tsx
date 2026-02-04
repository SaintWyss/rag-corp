import { act, renderHook } from "@testing-library/react";
import { useRagChat } from "@/features/rag";
import { SAMPLE_CHAT_STREAM } from "@/test/fixtures/sse";
import { getMockFetch, makeStreamResponse } from "@/test/helpers/mockFetch";
import { queryWorkspace } from "@/shared/api/api";

jest.mock("@/shared/api/api", () => ({
  queryWorkspace: jest.fn().mockResolvedValue({ matches: [] }),
  getWorkspaceDocument: jest.fn(),
}));

describe("useRagChat Hook", () => {
  const mockFetch = getMockFetch();

  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("returns initial state", () => {
    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    expect(result.current.messages).toEqual([]);
    expect(result.current.input).toBe("");
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe("");
    expect(result.current.conversationId).toBeNull();
  });

  it("shows error for empty message", async () => {
    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    expect(result.current.error).toBe("Escribi una pregunta antes de enviar.");
  });

  it("streams tokens and updates conversation state", async () => {
    mockFetch.mockResolvedValueOnce(makeStreamResponse(SAMPLE_CHAT_STREAM));
    (queryWorkspace as jest.Mock).mockResolvedValueOnce({ matches: [] });

    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

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
