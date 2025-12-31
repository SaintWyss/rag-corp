"use client";

type SourcesListProps = {
  sources: string[];
};

export function SourcesList({ sources }: SourcesListProps) {
  if (!sources.length) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
      <h3 className="text-xs uppercase tracking-[0.3em] text-white/50">
        Fuentes
      </h3>
      <div className="mt-4 space-y-3">
        {sources.map((source, index) => (
          <article
            key={`${index}-${source.slice(0, 12)}`}
            className="rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white/70"
          >
            {source}
          </article>
        ))}
      </div>
    </section>
  );
}
