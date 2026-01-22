const STORAGE_KEY = "ragcorp_api_key";

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function getStoredApiKey(): string {
  const storage = getStorage();
  if (!storage) {
    return "";
  }
  return storage.getItem(STORAGE_KEY) ?? "";
}

export function setStoredApiKey(value: string) {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  const trimmed = value.trim();
  if (trimmed) {
    storage.setItem(STORAGE_KEY, trimmed);
  } else {
    storage.removeItem(STORAGE_KEY);
  }
}
