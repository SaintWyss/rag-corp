/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/chat/components/ChatScreen.tsx (Screen chat)
===============================================================================
Responsabilidades:
  - Renderizar el chat con streaming y acciones del usuario.
  - Mantener estado de mensajes, reintentos y cancelaciones.
  - Mostrar feedback de errores y accesos rapidos a documentos.

Colaboradores:
  - features/rag/useRagChat
  - shared/ui/StatusBanner
  - next/link
===============================================================================
*/
"use client";

import { useRagChat } from "@/features/rag/useRagChat";
import { StatusBanner } from "@/shared/ui/StatusBanner";
import Link from "next/link";

type ChatScreenProps = {
  workspaceId?: string;
};

type WorkspaceChatScreenProps = {
  workspaceId: string;
};

export function ChatScreen({ workspaceId }: ChatScreenProps) {
  if (!workspaceId) {
    return <ChatEmptyState />;
  }

  return <WorkspaceChatScreen workspaceId={workspaceId} />;
}

function ChatEmptyState() {
  return (
    <section className="space-y-6">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold text-white">Chat</h1>
        <p className="mt-2 text-sm text-white/60">
          Selecciona un workspace para iniciar una conversacion con contexto.
        </p>
      </div>
      <Link
        href="/workspaces"
        className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-5 py-2 text-sm font-semibold text-white/70 transition hover:border-cyan-300 hover:text-cyan-300"
      >
        Ir a workspaces
      </Link>
    </section>
  );
}

function WorkspaceChatScreen({ workspaceId }: WorkspaceChatScreenProps) {
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
    <div className="flex w-full max-w-5xl flex-col gap-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-3 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs uppercase tracking-[0.2em] text-cyan-200 font-bold shadow-sm">
            Conversaciones en tiempo real
          </div>
          <div
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/50 font-bold"
            data-testid="chat-workspace"
          >
            Workspace {workspaceId}
          </div>
          <h1 className="text-3xl font-bold text-white sm:text-4xl drop-shadow-sm">
            Chat con streaming y contexto
          </h1>
          <p className="max-w-2xl text-sm text-white/60 font-medium">
            Envia varias preguntas y segui el hilo. Los tokens llegan en vivo
            desde el backend.
          </p>
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <button
            type="button"
            onClick={reset}
            data-testid="chat-reset-button"
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-bold uppercase tracking-[0.15em] text-white/60 transition hover:border-cyan-300 hover:text-cyan-300 hover:shadow-sm"
          >
            Nueva conversacion
          </button>
          {conversationId ? (
            <span className="text-xs text-white/30 font-mono">
              ID: {conversationId}
            </span>
          ) : null}
        </div>
      </header>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl backdrop-blur-md">
        <div
          className="flex max-h-[520px] flex-col gap-4 overflow-y-auto pr-2"
          data-testid="chat-message-list"
        >
          {messages.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-center text-sm text-white/30">
              Todavia no hay mensajes. Escribi una pregunta para comenzar.
            </div>
          ) : null}

          {messages.map((message) => {
            const isUser = message.role === "user";
            const bubbleStyles = isUser
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/10"
              : "bg-white/5 border border-white/10 text-white shadow-sm";
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
                  className={`w-full max-w-[85%] rounded-2xl px-5 py-4 ${bubbleStyles}`}
                >
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.content || statusText || " "}
                  </p>
                  {statusText && message.content ? (
                    <p
                      className={`mt-2 text-xs ${
                        isUser ? "text-cyan-200" : "text-white/40"
                      }`}
                    >
                      {statusText}
                    </p>
                  ) : null}
                  {message.verifiedSources && message.verifiedSources.length > 0 ? (
                    <div
                      className={`mt-4 border-t pt-3 ${
                        isUser ? "border-cyan-400/30" : "border-white/10"
                      }`}
                    >
                      <p
                        className={`text-xs uppercase tracking-[0.2em] ${
                          isUser ? "text-cyan-200" : "text-white/40 font-bold"
                        }`}
                      >
                        Fuentes verificadas
                      </p>
                      <ul
                        className={`mt-2 space-y-2 text-xs ${
                          isUser ? "text-cyan-100" : "text-white/70"
                        }`}
                      >
                        {message.verifiedSources.map((source) => (
                          <li
                            key={source.chunk_id}
                            className={`rounded-xl border p-3 ${
                              isUser
                                ? "border-cyan-400/30 bg-cyan-800/20"
                                : "border-white/10 bg-black/20"
                            }`}
                            data-testid="chat-verified-source"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <p
                                  className={`text-xs ${
                                    isUser ? "text-cyan-300" : "text-white/40"
                                  }`}
                                >
                                  Documento
                                </p>
                                <p className="text-sm font-semibold">
                                  {source.document_title || "Documento sin titulo"}
                                </p>
                              </div>
                              <Link
                                href={`/workspaces/${workspaceId}/documents?doc=${source.document_id}`}
                                className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] transition ${
                                  isUser
                                    ? "border-cyan-300 text-cyan-200 hover:bg-white/10"
                                    : "border-white/20 text-white/50 hover:border-cyan-300 hover:text-cyan-300 hover:bg-white/5"
                                }`}
                                data-testid="chat-source-open-doc"
                              >
                                Ver documento
                              </Link>
                            </div>
                            <p
                              className={`mt-2 text-[11px] font-mono ${
                                isUser ? "text-cyan-300" : "text-white/40"
                              }`}
                            >
                              Doc ID: {source.document_id}
                            </p>
                            <p className="mt-2 text-xs opacity-90">
                              {source.content}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : message.sources && message.sources.length > 0 ? (
                    <div
                      className={`mt-4 border-t pt-3 ${
                        isUser ? "border-cyan-400/30" : "border-white/10"
                      }`}
                    >
                      <p
                        className={`text-xs uppercase tracking-[0.2em] ${
                          isUser ? "text-cyan-200" : "text-white/40 font-bold"
                        }`}
                      >
                        Fuentes
                      </p>
                      <ul
                        className={`mt-2 space-y-2 text-xs ${
                          isUser ? "text-cyan-100" : "text-white/70"
                        }`}
                      >
                        {message.sources.map((source) => (
                          <li
                            key={source.chunk_id}
                            className={`rounded-xl border p-2 ${
                              isUser
                                ? "border-cyan-400/30 bg-cyan-800/20"
                                : "border-white/10 bg-black/20"
                            }`}
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
        className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-lg backdrop-blur-md"
        data-testid="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!loading) {
            void sendMessage(input);
          }
        }}
      >
        <label className="mb-3 block text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
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
          className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-inner transition-all"
          placeholder="Escribi tu pregunta... (Shift+Enter para nueva linea)"
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            data-testid="chat-send-button"
            className="rounded-full bg-cyan-400 px-6 py-2 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-400/20 transition hover:bg-cyan-300 hover:shadow-cyan-300/30 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/30 disabled:shadow-none"
          >
            {loading ? "Generando..." : "Enviar"}
          </button>
          {loading ? (
            <button
              type="button"
              onClick={cancel}
              data-testid="chat-cancel-button"
              className="rounded-full border border-white/10 bg-white/5 px-5 py-2 text-sm font-medium text-white/60 transition hover:bg-white/10 hover:text-white shadow-sm"
            >
              Cancelar
            </button>
          ) : null}
          {canRetry ? (
            <button
              type="button"
              onClick={() => void retryLast()}
              data-testid="chat-retry-button"
              className="rounded-full border border-white/10 bg-white/5 px-5 py-2 text-sm font-medium text-white/60 transition hover:bg-white/10 hover:text-white shadow-sm"
            >
              Reintentar
            </button>
          ) : null}
        </div>
      </form>
    </div>
  );
}
