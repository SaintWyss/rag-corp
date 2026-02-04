/**
===============================================================================
TARJETA CRC - apps/frontend/src/test/helpers/mockFetch.ts (Test fetch helpers)
===============================================================================
Responsabilidades:
  - Proveer helpers para mockear fetch de forma uniforme.
  - Evitar duplicación de stubs entre tests.
===============================================================================
*/

export type MockFetch = jest.Mock;

export function getMockFetch(): MockFetch {
  return global.fetch as MockFetch;
}

export function makeJsonResponse(status: number, data?: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: jest.fn().mockResolvedValue(data ? JSON.stringify(data) : ""),
  };
}

export function mockJsonOnce(status: number, data?: unknown) {
  getMockFetch().mockResolvedValueOnce(makeJsonResponse(status, data));
}

export function makeStreamResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  let index = 0;
  const reader = {
    read: jest.fn().mockImplementation(() => {
      if (index >= chunks.length) {
        return Promise.resolve({ value: undefined, done: true });
      }
      const value = encoder.encode(chunks[index++]);
      return Promise.resolve({ value, done: false });
    }),
  };

  return {
    ok: true,
    status: 200,
    body: { getReader: () => reader },
  };
}
