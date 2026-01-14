"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/AppShell";
import { NoticeBanner } from "../components/NoticeBanner";
import { StatusBanner } from "../components/StatusBanner";
import {
  getCurrentUser,
  getDocument,
  listDocuments,
  reprocessDocument,
  uploadDocument,
  type CurrentUser,
  type DocumentDetail,
  type DocumentStatus,
  type DocumentSummary,
} from "../lib/api";
import { getStoredApiKey } from "../lib/apiKey";

type UploadDraft = {
  title: string;
  source: string;
};

const emptyUpload: UploadDraft = {
  title: "",
  source: "",
};

const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

const STATUS_LABELS: Record<DocumentStatus, string> = {
  PENDING: "PENDING",
  PROCESSING: "PROCESSING",
  READY: "READY",
  FAILED: "FAILED",
};

const STATUS_STYLES: Record<DocumentStatus, string> = {
  PENDING: "border-amber-400/50 bg-amber-400/10 text-amber-100",
  PROCESSING: "border-sky-400/50 bg-sky-400/10 text-sky-100",
  READY: "border-emerald-400/50 bg-emerald-400/10 text-emerald-100",
  FAILED: "border-rose-400/50 bg-rose-400/10 text-rose-100",
};

function normalizeStatus(status?: DocumentStatus | null): DocumentStatus {
  if (!status) {
    return "READY";
  }
  return status;
}

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

function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1
  );
  const value = bytes / Math.pow(1024, index);
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function isAllowedFile(file: File): boolean {
  const lowerName = file.name.toLowerCase();
  const hasAllowedExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  return ALLOWED_MIME_TYPES.has(file.type) || hasAllowedExt;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [draft, setDraft] = useState<UploadDraft>(emptyUpload);
  const [file, setFile] = useState<File | null>(null);
  const [dropActive, setDropActive] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [apiKey, setApiKey] = useState("");

  const isAdmin = user?.role === "admin" || (!user && Boolean(apiKey));
  const isEmployee = user?.role === "employee";

  const loadDocuments = useCallback(async (preferredId?: string | null) => {
    setLoadingList(true);
    setError("");
    try {
      const res = await listDocuments();
      setDocuments(res.documents);
      const candidateId = preferredId ?? selectedId;
      const nextSelectedId = res.documents.length
        ? res.documents.some((doc) => doc.id === candidateId)
          ? candidateId
          : res.documents[0].id
        : null;
      setSelectedId(nextSelectedId ?? null);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoadingList(false);
      setRefreshTick((prev) => prev + 1);
    }
  }, [selectedId]);

  const loadDetail = useCallback(async (documentId: string) => {
    setLoadingDetail(true);
    setError("");
    try {
      const doc = await getDocument(documentId);
      setSelected(doc);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    setApiKey(getStoredApiKey());
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    loadDetail(selectedId);
  }, [selectedId, loadDetail, refreshTick]);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
        }
      })
      .catch((err) => {
        if (active) {
          setError(formatError(err));
        }
      })
      .finally(() => {
        if (active) {
          setAuthChecked(true);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const needsPolling = useMemo(
    () =>
      documents.some((doc) => {
        const status = normalizeStatus(doc.status);
        return status === "PENDING" || status === "PROCESSING";
      }),
    [documents]
  );

  useEffect(() => {
    if (!needsPolling) {
      return;
    }
    const interval = window.setInterval(() => {
      loadDocuments();
    }, 6000);
    return () => window.clearInterval(interval);
  }, [needsPolling, loadDocuments]);

  const metadataEntries = useMemo(() => {
    if (!selected?.metadata) {
      return [];
    }
    return Object.entries(selected.metadata);
  }, [selected]);

  const handleFileSelection = useCallback(
    (nextFile: File | null) => {
      if (!nextFile) {
        setFile(null);
        return;
      }
      if (!isAllowedFile(nextFile)) {
        setFile(null);
        setError("Solo se aceptan archivos PDF o DOCX.");
        return;
      }
      setError("");
      setFile(nextFile);
    },
    []
  );

  const handleFileInput = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const nextFile = event.target.files?.[0] ?? null;
      handleFileSelection(nextFile);
    },
    [handleFileSelection]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDropActive(false);
      const nextFile = event.dataTransfer.files?.[0] ?? null;
      handleFileSelection(nextFile);
    },
    [handleFileSelection]
  );

  const handleUpload = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!file) {
        setError("Selecciona un archivo para subir.");
        return;
      }
      setError("");
      setNotice("");
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        if (draft.title.trim()) {
          formData.append("title", draft.title.trim());
        }
        if (draft.source.trim()) {
          formData.append("source", draft.source.trim());
        }

        const result = await uploadDocument(formData);
        setNotice(`Archivo subido: ${result.file_name}. Procesando...`);
        setFile(null);
        setDraft(emptyUpload);
        setSelectedId(result.document_id);
        await loadDocuments(result.document_id);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setUploading(false);
      }
    },
    [draft, file, loadDocuments]
  );

  const handleReprocess = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    setError("");
    setNotice("");
    setReprocessing(true);
    try {
      const res = await reprocessDocument(selectedId);
      setNotice(`Reproceso encolado (${res.status}).`);
      await loadDocuments();
    } catch (err) {
      if (typeof err === "object" && err && "status" in err) {
        const status = (err as { status?: number }).status;
        if (status === 409) {
          setNotice("El documento ya esta en procesamiento.");
        } else {
          setError(formatError(err));
        }
      } else {
        setError(formatError(err));
      }
    } finally {
      setReprocessing(false);
    }
  }, [loadDocuments, selectedId]);

  const clearFile = useCallback(() => {
    setFile(null);
  }, []);

  const roleLabel = authChecked
    ? user
      ? user.role === "admin"
        ? "Admin"
        : "Empleado"
      : apiKey
        ? "API Key"
        : "Sin sesion"
    : "Verificando";

  return (
    <AppShell>
      <div className="space-y-8">
        <section className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold sm:text-4xl">Sources</h1>
            <span
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/60"
              data-testid="sources-role"
            >
              {roleLabel}
            </span>
          </div>
          <p className="max-w-2xl text-sm text-white/60 sm:text-base">
            Administra tus fuentes como en NotebookLM: sube PDFs/DOCX y monitorea
            el estado del procesamiento.
          </p>
        </section>

        <StatusBanner message={error} />
        <NoticeBanner message={notice} />

        {isAdmin ? (
          <section
            className="rounded-3xl border border-white/10 bg-white/5 p-6"
            data-testid="sources-upload-panel"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Subir fuente</h2>
                <p className="text-sm text-white/60">
                  PDF o DOCX. El procesamiento corre en background.
                </p>
              </div>
              <div className="text-xs text-white/50">
                {file ? formatFileSize(file.size) : "Selecciona un archivo"}
              </div>
            </div>

            <form
              onSubmit={handleUpload}
              className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_1fr]"
              data-testid="sources-upload-form"
            >
              <div
                className={`flex h-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed px-6 py-10 text-center transition ${
                  dropActive
                    ? "border-cyan-300/70 bg-cyan-400/10"
                    : "border-white/10 bg-slate-950/40"
                }`}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDropActive(true);
                }}
                onDragLeave={() => setDropActive(false)}
                onDrop={handleDrop}
                data-testid="sources-dropzone"
              >
                <input
                  id="sources-file-input"
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={handleFileInput}
                  data-testid="sources-file-input"
                  className="sr-only"
                />
                <label
                  htmlFor="sources-file-input"
                  className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white"
                >
                  Elegir archivo
                </label>
                <p className="text-xs text-white/50">
                  o arrastra y suelta aqui
                </p>
                {file ? (
                  <div className="mt-3 space-y-1 text-sm text-white">
                    <p className="font-semibold">{file.name}</p>
                    <p className="text-xs text-white/50">
                      {file.type || "Tipo desconocido"} · {formatFileSize(file.size)}
                    </p>
                    <button
                      type="button"
                      onClick={clearFile}
                      className="text-xs text-rose-200/80 hover:text-rose-100"
                      data-testid="sources-clear-file"
                    >
                      Quitar archivo
                    </button>
                  </div>
                ) : null}
              </div>

              <div className="space-y-4">
                <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                  Titulo (opcional)
                  <input
                    value={draft.title}
                    onChange={(event) =>
                      setDraft((prev) => ({
                        ...prev,
                        title: event.target.value,
                      }))
                    }
                    data-testid="sources-title-input"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                    placeholder="Guia comercial 2025"
                  />
                </label>
                <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                  Source (opcional)
                  <input
                    value={draft.source}
                    onChange={(event) =>
                      setDraft((prev) => ({
                        ...prev,
                        source: event.target.value,
                      }))
                    }
                    data-testid="sources-source-input"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                    placeholder="https://docs.example.com"
                  />
                </label>

                <button
                  type="submit"
                  disabled={uploading || !file}
                  data-testid="sources-upload-submit"
                  className="flex w-full items-center justify-center gap-2 rounded-full bg-cyan-500/80 px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-900/40 disabled:text-white/40"
                >
                  {uploading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                      Subiendo...
                    </span>
                  ) : (
                    "Subir archivo"
                  )}
                </button>
              </div>
            </form>
          </section>
        ) : (
          <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-lg font-semibold">Sources (solo lectura)</h2>
            <p className="text-sm text-white/60">
              Tu rol no permite cargar ni reprocesar archivos.
            </p>
          </section>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Listado</h2>
                <p className="text-sm text-white/60">
                  {documents.length} fuentes activas.
                </p>
              </div>
              <button
                type="button"
                onClick={loadDocuments}
                data-testid="sources-refresh"
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white"
              >
                {needsPolling ? "Actualizando..." : "Refrescar"}
              </button>
            </div>

            <div className="mt-6 space-y-3" data-testid="sources-list">
              {loadingList ? (
                <p className="text-sm text-white/50">Cargando fuentes...</p>
              ) : documents.length === 0 ? (
                <p className="text-sm text-white/50">
                  Aun no hay fuentes cargadas.
                </p>
              ) : (
                documents.map((doc) => {
                  const active = selectedId === doc.id;
                  const status = normalizeStatus(doc.status);
                  return (
                    <button
                      key={doc.id}
                      type="button"
                      onClick={() => setSelectedId(doc.id)}
                      data-testid="source-list-item"
                      data-document-id={doc.id}
                      data-document-title={doc.title}
                      className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                        active
                          ? "border-cyan-400/60 bg-cyan-400/10"
                          : "border-white/10 bg-slate-950/40 hover:border-cyan-400/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-white">
                              {doc.title}
                            </p>
                            <span
                              className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] ${
                                STATUS_STYLES[status]
                              }`}
                              data-testid="source-status-chip"
                              data-document-id={doc.id}
                            >
                              {STATUS_LABELS[status]}
                            </span>
                          </div>
                          <p className="text-xs text-white/50">
                            {doc.file_name || doc.source || "Sin archivo"}
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
            data-testid="source-detail"
            data-document-id={selected?.id}
            data-document-title={selected?.title}
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Detalle</h2>
                <p className="text-xs text-white/50">
                  Estado y metadata del documento.
                </p>
              </div>
              {isAdmin && selected ? (
                <button
                  type="button"
                  onClick={handleReprocess}
                  disabled={reprocessing || normalizeStatus(selected.status) === "PROCESSING"}
                  data-testid="source-reprocess-button"
                  className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white disabled:cursor-not-allowed disabled:text-white/40"
                >
                  {reprocessing ? "Reprocesando..." : "Reprocesar"}
                </button>
              ) : null}
            </div>

            {loadingDetail ? (
              <p className="mt-4 text-sm text-white/50">Cargando detalle...</p>
            ) : !selected ? (
              <p className="mt-4 text-sm text-white/50">
                Selecciona una fuente para ver sus detalles.
              </p>
            ) : (
              <div className="mt-4 space-y-4 text-sm text-white/70">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Titulo
                  </p>
                  <p
                    className="text-base text-white"
                    data-testid="source-detail-title"
                  >
                    {selected.title}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Archivo
                  </p>
                  <p data-testid="source-detail-file">
                    {selected.file_name || "Sin archivo"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    MIME
                  </p>
                  <p data-testid="source-detail-mime">
                    {selected.mime_type || "Sin tipo"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Estado
                  </p>
                  <span
                    className={`inline-flex rounded-full border px-3 py-1 text-xs uppercase tracking-[0.2em] ${
                      STATUS_STYLES[normalizeStatus(selected.status)]
                    }`}
                    data-testid="source-detail-status"
                  >
                    {STATUS_LABELS[normalizeStatus(selected.status)]}
                  </span>
                </div>
                {normalizeStatus(selected.status) === "FAILED" &&
                selected.error_message ? (
                  <div
                    className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-rose-100"
                    data-testid="source-detail-error"
                  >
                    {selected.error_message}
                  </div>
                ) : null}
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Source
                  </p>
                  <p data-testid="source-detail-source">
                    {selected.source || "Sin source"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Creado
                  </p>
                  <p data-testid="source-detail-created">
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
                      data-testid="source-detail-metadata"
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
              </div>
            )}
          </section>
        </div>

        {isEmployee ? (
          <p className="text-xs text-white/40">
            Modo empleado: solo lectura.
          </p>
        ) : null}
      </div>
    </AppShell>
  );
}
