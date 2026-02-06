/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/hooks/useRagChat.test.tsx
===============================================================================
Responsabilidades:
  - Validar estados y streaming del hook useRagChat.
  - Verificar errores y conversationId.

Colaboradores:
  - features/rag (hook)
  - test/helpers/mockFetch

Invariantes:
  - Sin llamadas reales de red.
===============================================================================
*/

import { act, renderHook } from "@testing-library/react";

import { useRagChat } from "@/features/rag";
import { queryWorkspace } from "@/shared/api/api";
import { SAMPLE_CHAT_STREAM } from "@/test/fixtures/sse";
import { getMockFetch, makeStreamResponse } from "@/test/helpers/mockFetch";

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

  it("shows error when workspace is missing", async () => {
    const { result } = renderHook(() => useRagChat({ workspaceId: "" }));

    await act(async () => {
      await result.current.sendMessage("hola");
    });

    expect(result.current.error).toBe(
      "Selecciona un workspace antes de preguntar."
    );
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

  it("marks error when response is not ok", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    await act(async () => {
      await result.current.sendMessage("hola");
    });

    expect(result.current.error).toMatch(/Error del servidor/);
    const assistant = result.current.messages.find(
      (msg) => msg.role === "assistant"
    );
    expect(assistant?.status).toBe("error");
  });

  it("fails when response body is empty", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: null,
    });

    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    await act(async () => {
      await result.current.sendMessage("hola");
    });

    expect(result.current.error).toBe("Respuesta vacia del servidor.");
  });

  it("handles error event in stream", async () => {
    const stream = [
      'event: error\ndata: {"error":"Fallo en stream"}\n\n',
    ];
    mockFetch.mockResolvedValueOnce(makeStreamResponse(stream));
    (queryWorkspace as jest.Mock).mockResolvedValueOnce({ matches: [] });

    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    await act(async () => {
      await result.current.sendMessage("hola");
    });

    expect(result.current.error).toBe("Fallo en stream");
    const assistant = result.current.messages.find(
      (msg) => msg.role === "assistant"
    );
    expect(assistant?.status).toBe("error");
  });

  it("cancels in-flight request", async () => {
    mockFetch.mockImplementationOnce((_url, options) => {
      return new Promise((_, reject) => {
        options?.signal?.addEventListener("abort", () => {
          const abortError = new Error("Aborted");
          abortError.name = "AbortError";
          reject(abortError);
        });
      });
    });

    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    await act(async () => {
      const promise = result.current.sendMessage("hola");
      result.current.cancel();
      await promise;
    });

    expect(result.current.error).toBe("Solicitud cancelada.");
    const assistant = result.current.messages.find(
      (msg) => msg.role === "assistant"
    );
    expect(assistant?.status).toBe("cancelled");
  });

  it("times out when stream exceeds timeout", async () => {
    jest.useFakeTimers();
    mockFetch.mockImplementationOnce((_url, options) => {
      return new Promise((_, reject) => {
        options?.signal?.addEventListener("abort", () => {
          const abortError = new Error("Aborted");
          abortError.name = "AbortError";
          reject(abortError);
        });
      });
    });

    const { result } = renderHook(() => useRagChat({ workspaceId: "ws-1" }));

    await act(async () => {
      const promise = result.current.sendMessage("hola");
      jest.advanceTimersByTime(31_000);
      await promise;
    });

    expect(result.current.error).toBe("Tiempo de espera agotado.");
    jest.useRealTimers();
  });
});
