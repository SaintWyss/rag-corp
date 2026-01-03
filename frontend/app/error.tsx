"use client";

import { useEffect } from "react";

/**
 * Global Error Boundary for Next.js App Router.
 *
 * Catches rendering errors in this route segment and displays
 * a user-friendly fallback UI with retry option.
 */
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
