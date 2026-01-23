"use client";

import { AuroraBackground } from "@/app/components/ui/aurora-background";
import { login } from "@/shared/api/api";
import { sanitizeNextPath } from "@/shared/lib/safeNext";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const next = sanitizeNextPath(sp.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Use centralized login from API client for consistent error handling
      await login(email, password);

      // Backend sets HttpOnly cookie. We don't need to store tokens in JS.
      router.replace(next);
      router.refresh();
    } catch (err) {
      // Extract error message
      if (err instanceof Error) {
        setError(err.message);
      } else if (typeof err === "object" && err && "message" in err) {
        setError(String(err.message));
      } else {
        setError("Login failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative w-full h-screen overflow-hidden">
      <AuroraBackground>
        <div className="z-10 flex items-center justify-center w-full h-full px-4">
          <div className="w-full max-w-md p-8 space-y-8 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl animate-fade-in-up">
            <div className="text-center space-y-2">
              <h1 className="text-4xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                Welcome Back
              </h1>
              <p className="text-gray-400 text-sm">
                Enter your credentials to access your workspace.
              </p>
            </div>

            <form className="mt-8 space-y-6" onSubmit={onSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 uppercase tracking-widest mb-1">
                    Email Address
                  </label>
                  <input
                    className="w-full px-4 py-3 text-white bg-black/20 border border-white/10 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-gray-600"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 uppercase tracking-widest mb-1">
                    Password
                  </label>
                  <input
                    className="w-full px-4 py-3 text-white bg-black/20 border border-white/10 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-gray-600"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                </div>
              </div>

              {error ? (
                <div className="p-3 text-sm text-red-200 bg-red-900/30 border border-red-500/30 rounded-lg backdrop-blur-sm animate-shake">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 text-sm font-bold text-white uppercase tracking-wider bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 rounded-xl shadow-lg shadow-indigo-500/20 transform transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  "Sign in"
                )}
              </button>
            </form>
          </div>
        </div>
      </AuroraBackground>
    </div>
  );
}
