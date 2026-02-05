/**
===============================================================================
TARJETA CRC - apps/frontend/app/(auth)/login/page.tsx (Login)
===============================================================================
Responsabilidades:
  - Renderizar la pantalla de login y coordinar el submit.
  - Aplicar redirect seguro despues de autenticar.

Colaboradores:
  - shared/ui/components/AuroraBackground
  - shared/api (auth)
  - shared/lib/safeNext
===============================================================================
*/
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent,useState } from "react";

import { getCurrentUser, login } from "@/shared/api/api";
import { sanitizeNextPath } from "@/shared/lib/safeNext";
import { AuroraBackground } from "@/shared/ui/components/AuroraBackground";

export default function LoginPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const next = sanitizeNextPath(sp.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Use centralized login from API client for consistent error handling
      await login(email, password);

      // Check role to decide destination
      const user = await getCurrentUser();
      let destination = next;

      if (user?.role === "admin") {
        // Prepare to go to Admin Console if defaulting to workspaces or explicitly asking for it
        if (destination === "/workspaces" || destination.startsWith("/workspaces")) {
          destination = "/admin/users";
        }
      } else {
        // Employee (or others): Ensure they don't go to admin console
        if (destination.startsWith("/admin")) {
          destination = "/workspaces";
        }
      }

      // Backend sets HttpOnly cookie. We don't need to store tokens in JS.
      router.replace(destination);
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
          <div className="w-full max-w-md p-8 space-y-8 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl animate-fade-in-up">
            <div className="text-center space-y-2">
              <h1 className="text-4xl font-bold tracking-tighter text-white drop-shadow-sm">
                Welcome Back
              </h1>
              <p className="text-white/60 text-sm font-medium">
                Enter your credentials to access your workspace.
              </p>
            </div>

            <form className="mt-8 space-y-6" onSubmit={onSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-widest mb-1">
                    Email Address
                  </label>
                  <input
                    className="w-full px-4 py-3 text-white bg-black/20 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-cyan-400/20 focus:border-cyan-400 transition-all placeholder:text-white/30 shadow-sm"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-white/50 uppercase tracking-widest mb-1">
                    Password
                  </label>
                  <input
                    className="w-full px-4 py-3 text-white bg-black/20 border border-white/10 rounded-xl outline-none focus:ring-4 focus:ring-cyan-400/20 focus:border-cyan-400 transition-all placeholder:text-white/30 shadow-sm"
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
                <div className="p-3 text-sm text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-lg animate-shake font-medium">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 text-sm font-bold text-slate-950 uppercase tracking-wider bg-cyan-400 hover:bg-cyan-300 rounded-xl shadow-lg shadow-cyan-400/20 transform transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
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
