"use client";

type SourcesListProps = {
  sources: string[];
};

export function SourcesList({ sources }: SourcesListProps) {
  if (!sources.length) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-white/40 bg-white/60 p-6 shadow-sm backdrop-blur-md">
      <h3 className="text-xs uppercase tracking-[0.3em] text-slate-500 font-bold">
        Fuentes
      </h3>
      <div className="mt-4 space-y-3">
        {sources.map((source, index) => (
          <article
            key={`${index}-${source.slice(0, 12)}`}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm"
          >
            {source}
          </article>
        ))}
      </div>
    </section>
  );
}
