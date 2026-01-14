/**
 * @fileoverview
 * Name: Home Page (RAG Chat UI)
 *
 * Responsibilities:
 *   - Render main RAG chat interface
 *   - Compose QueryForm, AnswerCard, SourcesList components
 *   - Wire useRagAsk hook to child components
 *   - Display error/status via StatusBanner
 *
 * Collaborators:
 *   - hooks/useRagAsk: state management and API call
 *   - components/QueryForm: user input
 *   - components/AnswerCard: displays LLM response
 *   - components/SourcesList: displays retrieved sources
 *   - components/StatusBanner: error display
 *   - components/PageHeader: branding
 *
 * Constraints:
 *   - Client component ("use client")
 *   - Must be responsive (mobile-first)
 *
 * Notes:
 *   - Uses Tailwind for styling with dark theme
 *   - Radial gradient backgrounds for visual appeal
 */
"use client";

import { AnswerCard } from "./components/AnswerCard";
import { AppShell } from "./components/AppShell";
import { PageHeader } from "./components/PageHeader";
import { QueryForm } from "./components/QueryForm";
import { SourcesList } from "./components/SourcesList";
import { StatusBanner } from "./components/StatusBanner";
import { useRagAsk } from "./hooks/useRagAsk";

export default function Home() {
  const { query, answer, sources, loading, error, setQuery, submit } =
    useRagAsk();

  return (
    <AppShell>
      <div className="flex max-w-5xl flex-col gap-8">
        <PageHeader />

        <QueryForm
          query={query}
          onQueryChange={setQuery}
          onSubmit={submit}
          loading={loading}
        />

        <StatusBanner message={error} />
        <AnswerCard answer={answer} />
        {sources.length > 0 ? <SourcesList sources={sources} /> : null}
      </div>
    </AppShell>
  );
}
