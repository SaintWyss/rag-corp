const STORAGE_KEY = "ragcorp_api_key";

export function getStoredApiKey(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(STORAGE_KEY) ?? "";
}

export function setStoredApiKey(value: string) {
  if (typeof window === "undefined") {
    return;
  }
  const trimmed = value.trim();
  if (trimmed) {
    window.localStorage.setItem(STORAGE_KEY, trimmed);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}
