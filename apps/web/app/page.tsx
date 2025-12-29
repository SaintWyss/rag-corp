"use client";

import { useState } from "react";
// Importamos el cliente generado automáticamente
import { queryV1QueryPost as query } from "@contracts/src/generated";

// Definimos el tipo de la respuesta para usarlo en el estado
// (Podríamos importarlo también, pero para el MVP lo inferimos o definimos simple)
type Match = {
  content: string;
  score: number;
};

export default function Home() {
  const [text, setText] = useState("");
  const [results, setResults] = useState<Match[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // LLAMADA AL BACKEND:
      // Usamos la función generada. Como configuramos el proxy en next.config.mjs,
      // la llamada va a /v1/query (relativo) y Next la manda al Python.
      const res = await query({ query: text, top_k: 3 });
      
      // Orval con fetch devuelve la respuesta cruda, necesitamos el JSON.
      // NOTA: Si usáramos axios con Orval, esto sería directo 'res.data'.
      // Con fetch nativo, 'query' hace el fetch y devuelve la Promise<Response>.
      // Sin embargo, el tipo generado por Orval en modo 'fetch' suele devolver la Promise<Response>.
      // Vamos a asumir comportamiento estándar de fetch generado.
      
      // Ajuste: Orval fetch mode a veces genera una función que devuelve el DTO directo 
      // O devuelve el Response. Depende de la config.
      // Vamos a probar asumiendo que devuelve el objeto Response de fetch.
      // Si falla, ajustamos.
      
      if (res.status === 200) {
          const data = await res.json();
          setResults(data.matches || []);
      }
    } catch (err) {
      console.error(err);
      alert("Error buscando");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-24 bg-slate-950 text-white">
      <h1 className="text-4xl font-bold mb-8">RAG Corp Search</h1>
      
      <form onSubmit={handleSearch} className="w-full max-w-md flex gap-2">
        <input
          className="flex-1 p-3 rounded text-black"
          placeholder="Preguntale a tus documentos..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button 
          disabled={loading}
          className="bg-blue-600 px-6 py-3 rounded hover:bg-blue-500 disabled:opacity-50"
        >
          {loading ? "..." : "Buscar"}
        </button>
      </form>

      <div className="mt-10 w-full max-w-2xl space-y-4">
        {results.map((r, i) => (
          <div key={i} className="p-4 border border-slate-700 rounded bg-slate-900">
            <p className="text-gray-300">{r.content}</p>
            <div className="mt-2 text-xs text-blue-400">Score: {r.score.toFixed(4)}</div>
          </div>
        ))}
        {results.length === 0 && !loading && (
          <p className="text-gray-500 text-center">Sin resultados aún.</p>
        )}
      </div>
    </main>
  );
}
