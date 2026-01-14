/**
 * @fileoverview
 * Name: useApiKey Hook
 *
 * Responsibilities:
 *   - Read/write API key from localStorage
 *   - Provide state for UI input
 *
 * Notes:
 *   - Client-only (uses localStorage)
 */
"use client";

import { useCallback, useState } from "react";
import { getStoredApiKey, setStoredApiKey } from "../lib/apiKey";

export function useApiKey() {
  const [apiKey, setApiKeyState] = useState(() => getStoredApiKey());

  const setApiKey = useCallback((value: string) => {
    setApiKeyState(value);
    setStoredApiKey(value);
  }, []);

  return { apiKey, setApiKey };
}
