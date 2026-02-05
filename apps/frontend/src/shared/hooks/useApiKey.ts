/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/hooks/useApiKey.ts (Hook API key)
===============================================================================
Responsabilidades:
  - Leer/escribir API key en sessionStorage.
  - Exponer estado para inputs de UI.

Colaboradores:
  - shared/lib/apiKey

Invariantes:
  - Solo corre en cliente (sessionStorage).
===============================================================================
*/
"use client";

import { useCallback, useState } from "react";

import { getStoredApiKey, setStoredApiKey } from "@/shared/lib/apiKey";

export function useApiKey() {
  const [apiKey, setApiKeyState] = useState(() => getStoredApiKey());

  const setApiKey = useCallback((value: string) => {
    setApiKeyState(value);
    setStoredApiKey(value);
  }, []);

  return { apiKey, setApiKey };
}
