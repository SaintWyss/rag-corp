/**
 * @fileoverview
 * Name: Error Boundary Component
 *
 * Responsibilities:
 *   - Catch unhandled errors in route segment
 *   - Display user-friendly error UI
 *   - Provide retry button to reset error state
 *   - Log errors to console (extensible to tracking service)
 *
 * Collaborators:
 *   - Next.js App Router: provides error/reset props
 *   - Future: error tracking service (Sentry, etc.)
 *
 * Constraints:
 *   - Must be client component ("use client")
 *   - Must handle both known and unknown errors
 *   - Must show digest ID when available
 *
 * Notes:
 *   - Spanish UI text ("Algo salió mal")
 *   - Dark theme consistent with app design
 *   - Emoji for visual error indication
 */
"use client";

import { useEffect } from "react";
export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log error to console (could integrate with error tracking service)
        console.error("Error boundary caught:", error);
    }, [error]);

    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-4 text-white">
            <div className="w-full max-w-md rounded-xl border border-red-500/30 bg-red-950/20 p-8 text-center">
                <div className="mb-4 text-5xl">⚠️</div>
                <h2 className="mb-2 text-xl font-semibold text-red-400">
                    Algo salió mal
                </h2>
                <p className="mb-6 text-sm text-slate-400">
                    {error.message || "Ocurrió un error inesperado."}
                </p>
                {error.digest && (
                    <p className="mb-4 font-mono text-xs text-slate-500">
                        ID: {error.digest}
                    </p>
                )}
                <button
                    onClick={reset}
                    className="rounded-lg bg-cyan-600 px-6 py-2.5 font-medium text-white transition-colors hover:bg-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-slate-950"
                >
                    Reintentar
                </button>
            </div>
        </div>
    );
}
