/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/shared/apiKey.test.tsx (API key storage)
===============================================================================
Responsabilidades:
  - Verificar persistencia en sessionStorage.
  - Asegurar comportamiento del hook useApiKey.

Colaboradores:
  - src/shared/lib/apiKey
  - src/shared/hooks/useApiKey
===============================================================================
*/

import { act, renderHook } from "@testing-library/react";

import { useApiKey } from "@/shared/hooks/useApiKey";
import { getStoredApiKey, setStoredApiKey } from "@/shared/lib/apiKey";

describe("shared/lib/apiKey", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("getStoredApiKey devuelve vacio si no hay clave", () => {
    expect(getStoredApiKey()).toBe("");
  });

  it("setStoredApiKey guarda y normaliza", () => {
    setStoredApiKey("  abc  ");
    expect(getStoredApiKey()).toBe("abc");
  });

  it("setStoredApiKey elimina si viene vacio", () => {
    setStoredApiKey("token");
    setStoredApiKey("   ");
    expect(getStoredApiKey()).toBe("");
  });
});

describe("shared/hooks/useApiKey", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("sincroniza estado y storage", () => {
    const { result } = renderHook(() => useApiKey());
    expect(result.current.apiKey).toBe("");

    act(() => {
      result.current.setApiKey("token-1");
    });

    expect(result.current.apiKey).toBe("token-1");
    expect(getStoredApiKey()).toBe("token-1");
  });
});
