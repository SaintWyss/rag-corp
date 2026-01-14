"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/AppShell";
import { NoticeBanner } from "../components/NoticeBanner";
import { StatusBanner } from "../components/StatusBanner";
import {
  deleteDocument,
  getDocument,
  ingestBatch,
  ingestText,
  listDocuments,
  type DocumentDetail,
  type DocumentSummary,
} from "../lib/api";

type DraftDocument = {
  title: string;
  text: string;
  source: string;
};

const emptyDraft: DraftDocument = {
  title: "",
  text: "",
  source: "",
};

function formatError(error: unknown): string {
  if (!error) {
    return "Error inesperado.";
  }
  if (typeof error === "string") {
    return error;
  }
  if (typeof error === "object" && "message" in error) {
    return String((error as { message?: string }).message || "Error inesperado.");
  }
  return "Error inesperado.";
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "Sin fecha";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [drafts, setDrafts] = useState<DraftDocument[]>([emptyDraft]);

  const loadDocuments = useCallback(async () => {
    setLoadingList(true);
    setError("");
    try {
      const res = await listDocuments();
      setDocuments(res.documents);
      if (!res.documents.length) {
        setSelectedId(null);
      } else if (!selectedId) {
        setSelectedId(res.documents[0].id);
      } else if (!res.documents.some((doc) => doc.id === selectedId)) {
        setSelectedId(res.documents[0].id);
      }
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoadingList(false);
    }
  }, [selectedId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }

    let active = true;
    setLoadingDetail(true);
    setError("");

    getDocument(selectedId)
      .then((doc) => {
        if (active) {
          setSelected(doc);
        }
      })
      .catch((err) => {
        if (active) {
          setError(formatError(err));
        }
      })
      .finally(() => {
        if (active) {
          setLoadingDetail(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedId]);

  const updateDraft = useCallback(
    (index: number, field: keyof DraftDocument, value: string) => {
      setDrafts((prev) =>
        prev.map((draft, idx) =>
          idx === index ? { ...draft, [field]: value } : draft
        )
      );
    },
    []
  );

  const addDraft = useCallback(() => {
    setDrafts((prev) => [...prev, emptyDraft]);
  }, []);

  const removeDraft = useCallback((index: number) => {
    setDrafts((prev) =>
      prev.length === 1 ? prev : prev.filter((_, idx) => idx !== index)
    );
  }, []);

  const handleIngest = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setError("");
      setNotice("");

      const prepared = drafts.map((draft) => ({
        title: draft.title.trim(),
        text: draft.text.trim(),
        source: draft.source.trim() || undefined,
      }));

      const invalid = prepared.some((doc) => !doc.title || !doc.text);
      if (invalid) {
        setError("Completa titulo y texto en todos los documentos.");
        return;
      }

      setIngesting(true);
      try {
        if (prepared.length > 1) {
          const res = await ingestBatch({ documents: prepared });
          setNotice(
            `Batch listo: ${res.documents.length} documentos (${res.total_chunks} chunks).`
          );
        } else {
          const res = await ingestText(prepared[0]);
          setNotice(
            `Documento listo: ${res.document_id} (${res.chunks} chunks).`
          );
        }
        setDrafts([emptyDraft]);
        await loadDocuments();
      } catch (err) {
        setError(formatError(err));
      } finally {
        setIngesting(false);
      }
    },
    [drafts, loadDocuments]
  );

  const handleDelete = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    const confirmed = window.confirm(
      "Seguro que queres borrar este documento?"
    );
    if (!confirmed) {
      return;
    }
    setError("");
    setNotice("");
    try {
      await deleteDocument(selectedId);
      setNotice("Documento eliminado.");
      setSelectedId(null);
      await loadDocuments();
    } catch (err) {
      setError(formatError(err));
    }
  }, [selectedId, loadDocuments]);

  const metadataEntries = useMemo(() => {
    if (!selected?.metadata) {
      return [];
    }
    return Object.entries(selected.metadata);
  }, [selected]);

  return (
    <AppShell>
      <div className="space-y-8">
        <section className="space-y-3">
          <h1 className="text-3xl font-semibold sm:text-4xl">
            Documentos y carga
          </h1>
          <p className="max-w-2xl text-sm text-white/60 sm:text-base">
            Ingesta documentos, revisa metadatos y administra tu corpus con
            permisos RBAC.
          </p>
        </section>

        <StatusBanner message={error} />
        <NoticeBanner message={notice} />

        <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Ingesta de documentos</h2>
              <p className="text-sm text-white/60">
                Carga uno o varios documentos para indexar.
              </p>
            </div>
            <button
              type="button"
              onClick={addDraft}
              data-testid="documents-add-draft"
              className="self-start rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white"
            >
              Agregar documento
            </button>
          </div>

          <form
            onSubmit={handleIngest}
            className="mt-6 space-y-6"
            data-testid="documents-ingest-form"
          >
            {drafts.map((draft, index) => (
              <div
                key={`draft-${index}`}
                className="rounded-2xl border border-white/10 bg-slate-950/40 p-4"
                data-testid="documents-draft"
                data-draft-index={index}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="text-sm font-semibold text-white/80">
                    Documento {index + 1}
                  </h3>
                  <button
                    type="button"
                    onClick={() => removeDraft(index)}
                    data-testid="documents-remove-draft"
                    data-draft-index={index}
                    className="text-xs text-white/50 hover:text-rose-200"
                  >
                    Quitar
                  </button>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                    Titulo
                    <input
                      value={draft.title}
                      onChange={(event) =>
                        updateDraft(index, "title", event.target.value)
                      }
                      data-testid="documents-title-input"
                      data-draft-index={index}
                      className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                      placeholder="Guia de onboarding"
                    />
                  </label>
                  <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                    Source (opcional)
                    <input
                      value={draft.source}
                      onChange={(event) =>
                        updateDraft(index, "source", event.target.value)
                      }
                      data-testid="documents-source-input"
                      data-draft-index={index}
                      className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                      placeholder="https://docs.example.com/intro"
                    />
                  </label>
                </div>
                <label className="mt-4 block space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                  Texto
                  <textarea
                    value={draft.text}
                    onChange={(event) =>
                      updateDraft(index, "text", event.target.value)
                    }
                    data-testid="documents-text-input"
                    data-draft-index={index}
                    className="min-h-[120px] w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                    placeholder="Pega el texto del documento..."
                  />
                </label>
              </div>
            ))}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-xs text-white/50">
                {drafts.length > 1
                  ? "Se enviara como batch."
                  : "Se enviara como documento unico."}
              </span>
              <button
                type="submit"
                disabled={ingesting}
                data-testid="documents-ingest-submit"
                className="rounded-full bg-cyan-500/80 px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-900/40 disabled:text-white/40"
              >
                {ingesting ? "Procesando..." : "Ingestar"}
              </button>
            </div>
          </form>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Listado</h2>
                <p className="text-sm text-white/60">
                  {documents.length} documentos activos.
                </p>
              </div>
              <button
                type="button"
                onClick={loadDocuments}
                data-testid="documents-reload"
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white"
              >
                Recargar
              </button>
            </div>

            <div className="mt-6 space-y-3" data-testid="documents-list">
              {loadingList ? (
                <p className="text-sm text-white/50">Cargando documentos...</p>
              ) : documents.length === 0 ? (
                <p className="text-sm text-white/50">
                  Aun no hay documentos cargados.
                </p>
              ) : (
                documents.map((doc) => {
                  const active = selectedId === doc.id;
                  return (
                    <button
                      key={doc.id}
                      type="button"
                      onClick={() => setSelectedId(doc.id)}
                      data-testid="document-list-item"
                      data-document-id={doc.id}
                      data-document-title={doc.title}
                      className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                        active
                          ? "border-cyan-400/60 bg-cyan-400/10"
                          : "border-white/10 bg-slate-950/40 hover:border-cyan-400/40"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-white">
                            {doc.title}
                          </p>
                          <p className="text-xs text-white/50">
                            {doc.source || "Sin source"}
                          </p>
                        </div>
                        <span className="text-xs text-white/40">
                          {formatDate(doc.created_at)}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <section
            className="rounded-3xl border border-white/10 bg-white/5 p-6"
            data-testid="document-detail"
            data-document-id={selected?.id}
            data-document-title={selected?.title}
          >
            <h2 className="text-lg font-semibold">Detalle</h2>
            {loadingDetail ? (
              <p className="mt-4 text-sm text-white/50">Cargando detalle...</p>
            ) : !selected ? (
              <p className="mt-4 text-sm text-white/50">
                Selecciona un documento para ver sus detalles.
              </p>
            ) : (
              <div className="mt-4 space-y-4 text-sm text-white/70">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Titulo
                  </p>
                  <p
                    className="text-base text-white"
                    data-testid="document-detail-title"
                  >
                    {selected.title}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Source
                  </p>
                  <p data-testid="document-detail-source">
                    {selected.source || "Sin source"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Creado
                  </p>
                  <p data-testid="document-detail-created">
                    {formatDate(selected.created_at)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Metadata
                  </p>
                  {metadataEntries.length === 0 ? (
                    <p className="text-white/50">Sin metadata.</p>
                  ) : (
                    <ul
                      className="space-y-2"
                      data-testid="document-detail-metadata"
                    >
                      {metadataEntries.map(([key, value]) => (
                        <li
                          key={key}
                          className="rounded-xl border border-white/10 bg-slate-950/40 px-3 py-2 text-xs text-white/70"
                        >
                          <span className="text-white/40">{key}: </span>
                          {typeof value === "string"
                            ? value
                            : JSON.stringify(value)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleDelete}
                  data-testid="document-delete-button"
                  className="w-full rounded-full border border-rose-400/40 px-4 py-2 text-sm text-rose-100 transition hover:border-rose-300/70 hover:bg-rose-500/10"
                >
                  Borrar documento
                </button>
              </div>
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
}
