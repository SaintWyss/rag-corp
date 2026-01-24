/**
 * @fileoverview
 * Name: AnswerCard Component
 *
 * Responsibilities:
 *   - Display LLM-generated answer text
 *   - Show model badge ("Gemini")
 *   - Render nothing if answer is empty
 *   - Announce content changes via aria-live
 *
 * Collaborators:
 *   - page.tsx: parent that passes answer prop
 *   - useRagAsk: provides answer state
 *
 * Constraints:
 *   - Must be accessible (aria-live for screen readers)
 *   - Conditionally renders (null when empty)
 *
 * Notes:
 *   - Gradient background for visual depth
 *   - Responsive text sizing (sm:text-lg)
 */
"use client";

type AnswerCardProps = {
  answer: string;
};

export function AnswerCard({ answer }: AnswerCardProps) {
  if (!answer) {
    return null;
  }

  return (
    <section
      className="rounded-3xl border border-white/40 bg-white/60 p-6 shadow-xl backdrop-blur-md"
      aria-labelledby="answer-heading"
      aria-live="polite"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2
          id="answer-heading"
          className="text-xs uppercase tracking-[0.3em] text-slate-500 font-bold"
        >
          Respuesta
        </h2>
        <span
          className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-indigo-700 font-bold"
          aria-label="Modelo: Gemini"
        >
          Gemini
        </span>
      </div>
      <p className="text-base leading-7 text-slate-800 sm:text-lg">
        {answer}
      </p>
    </section>
  );
}
