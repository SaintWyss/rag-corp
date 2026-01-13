import { act, renderHook } from "@testing-library/react";
import { useRagAsk } from "../../app/hooks/useRagAsk";

// Mock the generated API client
jest.mock("@contracts/src/generated", () => ({
    askV1AskPost: jest.fn(),
}));

import type { askV1AskPostResponse } from "@contracts/src/generated";
import { askV1AskPost } from "@contracts/src/generated";

const mockAskApi = askV1AskPost as jest.MockedFunction<typeof askV1AskPost>;

/**
 * Helper to create mock API responses.
 * Uses type assertion because we test error codes not in the OpenAPI spec (401, 429, 503, etc.)
 */
const makeResponse = (
    status: number,
    data: askV1AskPostResponse["data"] = { answer: "", sources: [] }
): askV1AskPostResponse => ({
    status,
    data,
} as askV1AskPostResponse);

describe("useRagAsk Hook", () => {
    beforeEach(() => {
        mockAskApi.mockClear();
    });

    it("returns initial state", () => {
        const { result } = renderHook(() => useRagAsk());

        expect(result.current.query).toBe("");
        expect(result.current.answer).toBe("");
        expect(result.current.sources).toEqual([]);
        expect(result.current.loading).toBe(false);
        expect(result.current.error).toBe("");
    });

    it("updates query when setQuery is called", () => {
        const { result } = renderHook(() => useRagAsk());

        act(() => {
            result.current.setQuery("test query");
        });

        expect(result.current.query).toBe("test query");
    });

    it("shows error for empty query", async () => {
        const { result } = renderHook(() => useRagAsk());

        await act(async () => {
            await result.current.submit();
        });

        expect(result.current.error).toBe("Escribi una pregunta antes de enviar.");
    });

    it("handles 401 unauthorized error", async () => {
        mockAskApi.mockResolvedValueOnce(makeResponse(401));

        const { result } = renderHook(() => useRagAsk());

        act(() => {
            result.current.setQuery("test");
        });

        await act(async () => {
            await result.current.submit();
        });

        expect(result.current.error).toContain("API key requerida");
    });

    it("handles 429 rate limit error", async () => {
        mockAskApi.mockResolvedValueOnce(makeResponse(429));

        const { result } = renderHook(() => useRagAsk());

        act(() => {
            result.current.setQuery("test");
        });

        await act(async () => {
            await result.current.submit();
        });

        expect(result.current.error).toContain("Demasiadas solicitudes");
    });

    it("handles 503 service unavailable", async () => {
        mockAskApi.mockResolvedValueOnce(makeResponse(503));

        const { result } = renderHook(() => useRagAsk());

        act(() => {
            result.current.setQuery("test");
        });

        await act(async () => {
            await result.current.submit();
        });

        expect(result.current.error).toContain("Servicio no disponible");
    });

    it("handles successful response", async () => {
        mockAskApi.mockResolvedValueOnce(
            makeResponse(200, {
                answer: "Test answer",
                sources: ["source1.pdf", "source2.pdf"],
            })
        );

        const { result } = renderHook(() => useRagAsk());

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
        mockAskApi.mockRejectedValueOnce(new Error("Network error"));

        const { result } = renderHook(() => useRagAsk());

        act(() => {
            result.current.setQuery("test");
        });

        await act(async () => {
            await result.current.submit();
        });

        expect(result.current.error).toContain("Error de conexión");
    });

    it("resets state when reset is called", () => {
        const { result } = renderHook(() => useRagAsk());

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
