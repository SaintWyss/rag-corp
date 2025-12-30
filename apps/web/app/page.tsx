"use client";

import { useState } from "react";
import { askV1AskPost } from "@contracts/src/generated";

export default function Home() {
  const [text, setText] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAnswer("");
    setSources([]);
    setError("");

    try {
      // Llamada al Backend (RAG)
      const res = await askV1AskPost(
        { query: text, top_k: 3 },
        {
          headers: { "Content-Type": "application/json" },
        }
      );

      if (res.status === 200) {
          setAnswer(res.data.answer);
          setSources(res.data.sources || []);
      } else {
          setError("Error en el servidor: " + res.status);
      }
    } catch (err) {
      console.error(err);
      setError("Error de conexión. ¿Está prendido el backend?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-8 font-sans">
      <div className="max-w-3xl mx-auto">

        {/* TÍTULO */}
        <h1 className="text-4xl font-bold mb-8 text-yellow-400 border-b border-gray-700 pb-4">
          RAG Corp v1.0
        </h1>

        {/* FORMULARIO */}
        <form onSubmit={handleSearch} className="flex gap-4 mb-8">
          <input
            className="flex-1 p-4 text-lg rounded bg-white text-black border-4 border-gray-600 focus:border-yellow-400 outline-none placeholder-gray-500 font-medium"
            placeholder="Escribí tu pregunta acá..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            disabled={loading}
            className="bg-yellow-500 text-black font-extrabold px-8 py-4 rounded hover:bg-yellow-400 disabled:opacity-50 text-xl tracking-wide uppercase"
          >
            {loading ? "Pensando..." : "Preguntar"}
          </button>
        </form>

        {/* MENSAJE DE ERROR */}
        {error && (
          <div className="bg-red-600 text-white p-4 rounded mb-8 font-bold border-2 border-red-400 text-lg">
            ⚠️ {error}
          </div>
        )}

        {/* RESPUESTA DE LA IA */}
        {answer && (
          <div className="bg-gray-900 border-2 border-yellow-600 p-8 rounded-lg mb-8 shadow-lg shadow-yellow-900/20">
            <h3 className="text-yellow-400 font-bold mb-4 uppercase text-sm tracking-widest border-b border-gray-700 pb-2">
              Respuesta Generada:
            </h3>
            <p className="text-2xl leading-relaxed text-white font-light">
              {answer}
            </p>
          </div>
        )}

        {/* FUENTES */}
        {sources.length > 0 && (
          <div className="bg-gray-950 border border-gray-800 p-6 rounded">
            <h4 className="text-gray-400 font-bold mb-4 text-xs uppercase tracking-wider">
              Basado en estos fragmentos:
            </h4>
            <ul className="space-y-3">
              {sources.map((src, i) => (
                <li key={i} className="text-base text-gray-300 bg-gray-900 p-3 rounded border border-gray-800 font-mono">
                  "{src}"
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}