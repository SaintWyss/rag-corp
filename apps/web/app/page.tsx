"use client";

import { AnswerCard } from "./components/AnswerCard";
import { PageHeader } from "./components/PageHeader";
import { QueryForm } from "./components/QueryForm";
import { SourcesList } from "./components/SourcesList";
import { StatusBanner } from "./components/StatusBanner";
import { useRagAsk } from "./hooks/useRagAsk";

export default function Home() {
  const { query, answer, sources, loading, error, setQuery, submit } =
    useRagAsk();

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.15),_transparent_55%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,_rgba(14,116,144,0.2),_transparent_45%)]" />
        <div className="relative mx-auto flex max-w-5xl flex-col gap-8 px-6 py-16 sm:px-10">
          <PageHeader />

          <QueryForm
            query={query}
            onQueryChange={setQuery}
            onSubmit={submit}
            loading={loading}
          />

          <StatusBanner message={error} />
          <AnswerCard answer={answer} />
          <SourcesList sources={sources} />
        </div>
      </div>
    </div>
  );
}
