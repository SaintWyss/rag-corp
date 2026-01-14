"use client";

import { useApiKey } from "../hooks/useApiKey";

export function ApiKeyInput() {
  const { apiKey, setApiKey } = useApiKey();

  return (
    <div className="flex flex-col gap-2 text-xs text-white/60 sm:text-sm">
      <label htmlFor="api-key" className="uppercase tracking-[0.2em]">
        API Key
      </label>
      <input
        id="api-key"
        type="password"
        value={apiKey}
        onChange={(event) => setApiKey(event.target.value)}
        placeholder="X-API-Key para entorno dev"
        className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
      />
    </div>
  );
}
