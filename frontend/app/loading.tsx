/**
 * Loading UI for Next.js App Router Suspense boundary.
 *
 * Displays a skeleton/spinner while the page is loading.
 */
export default function Loading() {
    return (
        <div className="min-h-screen bg-slate-950 text-white">
            <div className="relative overflow-hidden">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.15),_transparent_55%)]" />
                <div className="relative mx-auto flex max-w-5xl flex-col gap-8 px-6 py-16 sm:px-10">
                    {/* Header skeleton */}
                    <div className="flex flex-col items-center gap-4">
                        <div className="h-10 w-48 animate-pulse rounded-lg bg-slate-800" />
                        <div className="h-4 w-96 animate-pulse rounded bg-slate-800" />
                    </div>

                    {/* Form skeleton */}
                    <div className="flex flex-col gap-4">
                        <div className="h-24 w-full animate-pulse rounded-xl bg-slate-800/50" />
                        <div className="h-12 w-32 animate-pulse self-end rounded-lg bg-slate-800" />
                    </div>

                    {/* Answer skeleton */}
                    <div className="space-y-3">
                        <div className="h-4 w-full animate-pulse rounded bg-slate-800/50" />
                        <div className="h-4 w-5/6 animate-pulse rounded bg-slate-800/50" />
                        <div className="h-4 w-4/6 animate-pulse rounded bg-slate-800/50" />
                    </div>
                </div>
            </div>
        </div>
    );
}
