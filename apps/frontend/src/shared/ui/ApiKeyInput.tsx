"use client";

import { useApiKey } from "@/shared/hooks/useApiKey";

export function ApiKeyInput() {
  const { apiKey, setApiKey } = useApiKey();

  return (
    <div className="flex flex-col gap-2 text-xs text-white/50 font-bold sm:text-sm">
      <label htmlFor="api-key" className="uppercase tracking-[0.2em]">
        API Key
      </label>
      <input
        id="api-key"
        type="password"
        value={apiKey}
        onChange={(event) => setApiKey(event.target.value)}
        placeholder="X-API-Key para entorno dev"
        className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-sm transition-all"
      />
    </div>
  );
}
