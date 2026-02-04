"use client";

export function PageHeader() {
  return (
    <header className="space-y-4">
      <div className="inline-flex items-center gap-3 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-xs uppercase tracking-[0.2em] text-indigo-900 font-bold shadow-sm">
        RAG Corp · v1
      </div>
      <h1 className="text-3xl font-bold text-slate-900 sm:text-4xl lg:text-5xl drop-shadow-sm">
        Busqueda semantica con respuestas trazables
      </h1>
      <p className="max-w-2xl text-sm leading-6 text-slate-600 sm:text-base font-medium">
        Hace preguntas en lenguaje natural y obtene respuestas basadas
        unicamente en tus documentos. El sistema combina embeddings y Gemini
        para mantener el contexto controlado.
      </p>
    </header>
  );
}
