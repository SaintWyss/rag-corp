"use client";

export function PageHeader() {
  return (
    <header className="space-y-4">
      <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/60">
        RAG Corp · v1
      </div>
      <h1 className="text-3xl font-semibold text-white sm:text-4xl lg:text-5xl">
        Busqueda semantica con respuestas trazables
      </h1>
      <p className="max-w-2xl text-sm leading-6 text-white/60 sm:text-base">
        Hace preguntas en lenguaje natural y obtene respuestas basadas
        unicamente en tus documentos. El sistema combina embeddings y Gemini
        para mantener el contexto controlado.
      </p>
    </header>
  );
}
