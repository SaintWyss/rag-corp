/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/hooks/useRagAsk.test.tsx
===============================================================================
Responsabilidades:
  - Validar estados y errores del hook useRagAsk.
  - Verificar mapeo de errores HTTP.

Colaboradores:
  - features/rag (hook)
  - test/helpers/mockFetch

Invariantes:
  - Sin llamadas reales de red.
===============================================================================
*/

import { act, renderHook } from "@testing-library/react";

import { useRagAsk } from "@/features/rag";
import { HTTP_ERROR_FIXTURES } from "@/test/fixtures/httpErrors";
import { getMockFetch, mockJsonOnce } from "@/test/helpers/mockFetch";

const mockFetch = getMockFetch();

describe("useRagAsk Hook", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("returns initial state", () => {
    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    expect(result.current.query).toBe("");
    expect(result.current.answer).toBe("");
    expect(result.current.sources).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe("");
  });

  it("updates query when setQuery is called", () => {
    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("test query");
    });

    expect(result.current.query).toBe("test query");
  });

  it("shows error for empty query", async () => {
    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    await act(async () => {
      await result.current.submit();
    });

    expect(result.current.error).toBe("Escribi una pregunta antes de enviar.");
  });

  it("handles 401 unauthorized error", async () => {
    mockJsonOnce(HTTP_ERROR_FIXTURES.unauthorized.status);

    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("test");
    });

    await act(async () => {
      await result.current.submit();
    });

    expect(result.current.error).toBe(HTTP_ERROR_FIXTURES.unauthorized.message);
  });

  it("handles 429 rate limit error", async () => {
    mockJsonOnce(HTTP_ERROR_FIXTURES.rateLimit.status);

    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("test");
    });

    await act(async () => {
      await result.current.submit();
    });

    expect(result.current.error).toBe(HTTP_ERROR_FIXTURES.rateLimit.message);
  });

  it("handles 503 service unavailable", async () => {
    mockJsonOnce(HTTP_ERROR_FIXTURES.serviceUnavailable.status);

    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("test");
    });

    await act(async () => {
      await result.current.submit();
    });

    expect(result.current.error).toBe(
      HTTP_ERROR_FIXTURES.serviceUnavailable.message
    );
  });

  it("handles successful response", async () => {
    mockJsonOnce(200, {
      answer: "Test answer",
      sources: ["source1.pdf", "source2.pdf"],
    });

    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("test query");
    });

    await act(async () => {
      await result.current.submit();
    });

    expect(result.current.answer).toBe("Test answer");
    expect(result.current.sources).toEqual(["source1.pdf", "source2.pdf"]);
    expect(result.current.error).toBe("");
  });

  it("handles network error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("test");
    });

    await act(async () => {
      await result.current.submit();
    });

    expect(result.current.error).toContain("Error de conexión");
  });

  it("resets state when reset is called", () => {
    const { result } = renderHook(() => useRagAsk({ workspaceId: "ws-1" }));

    act(() => {
      result.current.setQuery("some query");
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.query).toBe("");
    expect(result.current.answer).toBe("");
    expect(result.current.error).toBe("");
  });
});
