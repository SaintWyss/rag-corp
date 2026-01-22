/**
 * @fileoverview
 * Name: Chat Page (Streaming RAG)
 *
 * Responsibilities:
 *   - Render streaming multi-turn chat UI
 *   - Connect to useRagChat hook
 *   - Show messages, sources, and input controls
 */
"use client";

import Link from "next/link";
import { AppShell } from "../../../components/AppShell";
import { StatusBanner } from "../../../components/StatusBanner";
import { useRagChat } from "../../../hooks/useRagChat";

type PageProps = {
  params: {
    id: string;
  };
};

export default function ChatPage({ params }: PageProps) {
  const workspaceId = params.id;
  const {
    messages,
    input,
    loading,
    error,
    conversationId,
    setInput,
    sendMessage,
    cancel,
    retryLast,
    reset,
  } = useRagChat({ workspaceId });

  const lastAssistant = [...messages]
    .reverse()
    .find((message) => message.role === "assistant");
  const canRetry =
    lastAssistant?.status === "error" || lastAssistant?.status === "cancelled";

  return (
    <AppShell>
      <div className="flex w-full max-w-5xl flex-col gap-8">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/60">
              Conversaciones en tiempo real
            </div>
            <div
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60"
              data-testid="chat-workspace"
            >
              Workspace {workspaceId}
            </div>
            <h1 className="text-3xl font-semibold text-white sm:text-4xl">
              Chat con streaming y contexto
            </h1>
            <p className="max-w-2xl text-sm text-white/60">
              Envia varias preguntas y segui el hilo. Los tokens llegan en
              vivo desde el backend.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 sm:items-end">
            <button
              type="button"
              onClick={reset}
              data-testid="chat-reset-button"
              className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-white/70 transition hover:bg-white/10"
            >
              Nueva conversacion
            </button>
            {conversationId ? (
              <span className="text-xs text-white/40">
                ID: {conversationId}
              </span>
            ) : null}
          </div>
        </header>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <div
            className="flex max-h-[520px] flex-col gap-4 overflow-y-auto pr-2"
            data-testid="chat-message-list"
          >
            {messages.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-white/60">
                Todavia no hay mensajes. Escribi una pregunta para comenzar.
              </div>
            ) : null}

            {messages.map((message) => {
              const isUser = message.role === "user";
              const bubbleStyles = isUser
                ? "bg-cyan-400/20 text-white"
                : "bg-white/10 text-white/90";
              const alignment = isUser ? "justify-end" : "justify-start";
              const statusText =
                message.status === "streaming"
                  ? "Generando..."
                  : message.status === "cancelled"
                  ? "Respuesta cancelada"
                  : message.status === "error"
                  ? "Respuesta con error"
                  : "";

              return (
                <div
                  key={message.id}
                  className={`flex ${alignment}`}
                  data-testid="chat-message"
                  data-role={message.role}
                  data-status={message.status ?? "complete"}
                >
                  <div
                    className={`w-full max-w-[85%] rounded-2xl px-4 py-3 ${bubbleStyles}`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content || statusText || " "}
                    </p>
                    {statusText && message.content ? (
                      <p className="mt-2 text-xs text-white/50">
                        {statusText}
                      </p>
                    ) : null}
                    {message.verifiedSources && message.verifiedSources.length > 0 ? (
                      <div className="mt-3 border-t border-white/10 pt-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-white/50">
                          Fuentes verificadas
                        </p>
                        <ul className="mt-2 space-y-2 text-xs text-white/70">
                          {message.verifiedSources.map((source) => (
                            <li
                              key={source.chunk_id}
                              className="rounded-xl border border-white/10 bg-white/5 p-3"
                              data-testid="chat-verified-source"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div>
                                  <p className="text-xs text-white/50">
                                    Documento
                                  </p>
                                  <p className="text-sm text-white">
                                    {source.document_title || "Documento sin titulo"}
                                  </p>
                                </div>
                                <Link
                                  href={`/workspaces/${workspaceId}/documents?doc=${source.document_id}`}
                                  className="rounded-full border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/70 transition hover:border-cyan-300/50 hover:text-white"
                                  data-testid="chat-source-open-doc"
                                >
                                  Ver documento
                                </Link>
                              </div>
                              <p className="mt-2 text-[11px] text-white/40">
                                Doc ID: {source.document_id}
                              </p>
                              <p className="mt-2 text-xs text-white/70">
                                {source.content}
                              </p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : message.sources && message.sources.length > 0 ? (
                      <div className="mt-3 border-t border-white/10 pt-3">
                        <p className="text-xs uppercase tracking-[0.2em] text-white/50">
                          Fuentes
                        </p>
                        <ul className="mt-2 space-y-2 text-xs text-white/70">
                          {message.sources.map((source) => (
                            <li
                              key={source.chunk_id}
                              className="rounded-xl border border-white/10 bg-white/5 p-2"
                              data-testid="chat-source"
                            >
                              {source.content}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <StatusBanner message={error} />

        <form
          className="rounded-3xl border border-white/10 bg-white/5 p-6"
          data-testid="chat-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!loading) {
              void sendMessage(input);
            }
          }}
        >
          <label className="mb-3 block text-xs uppercase tracking-[0.2em] text-white/50">
            Mensaje
          </label>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (!loading) {
                  void sendMessage(input);
                }
              }
            }}
            rows={4}
            data-testid="chat-input"
            className="w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:border-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-300/30"
            placeholder="Escribi tu pregunta... (Shift+Enter para nueva linea)"
          />

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              data-testid="chat-send-button"
              className="rounded-full bg-cyan-400/80 px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-white/20 disabled:text-white/50"
            >
              {loading ? "Generando..." : "Enviar"}
            </button>
            {loading ? (
              <button
                type="button"
                onClick={cancel}
                data-testid="chat-cancel-button"
                className="rounded-full border border-white/20 px-5 py-2 text-sm text-white/70 transition hover:bg-white/10"
              >
                Cancelar
              </button>
            ) : null}
            {canRetry ? (
              <button
                type="button"
                onClick={() => void retryLast()}
                data-testid="chat-retry-button"
                className="rounded-full border border-white/20 px-5 py-2 text-sm text-white/70 transition hover:bg-white/10"
              >
                Reintentar
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </AppShell>
  );
}
