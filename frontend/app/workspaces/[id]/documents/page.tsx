"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { NoticeBanner } from "../../../components/NoticeBanner";
import { StatusBanner } from "../../../components/StatusBanner";
import {
  getCurrentUser,
  deleteWorkspaceDocument,
  getWorkspaceDocument,
  listWorkspaceDocuments,
  reprocessWorkspaceDocument,
  uploadWorkspaceDocument,
  type CurrentUser,
  type DocumentDetail,
  type DocumentStatus,
  type DocumentSummary,
  type DocumentSort,
} from "../../../lib/api";
import { getStoredApiKey } from "../../../lib/apiKey";

type UploadDraft = {
  title: string;
  source: string;
  tags: string;
};

type StatusFilter = "ALL" | DocumentStatus;

const emptyUpload: UploadDraft = {
  title: "",
  source: "",
  tags: "",
};

const PAGE_SIZE = 20;

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

const STATUS_FILTERS: Array<{ value: StatusFilter; label: string }> = [
  { value: "ALL", label: "Todos" },
  { value: "PENDING", label: "Pending" },
  { value: "PROCESSING", label: "Processing" },
  { value: "READY", label: "Ready" },
  { value: "FAILED", label: "Failed" },
];

const SORT_OPTIONS: Array<{ value: DocumentSort; label: string }> = [
  { value: "created_at_desc", label: "Mas recientes" },
  { value: "created_at_asc", label: "Mas antiguos" },
  { value: "title_asc", label: "Titulo A-Z" },
  { value: "title_desc", label: "Titulo Z-A" },
];

function normalizeStatus(status?: DocumentStatus | null): DocumentStatus {
  if (!status) {
    return "READY";
  }
  return status;
}

function normalizeTags(doc: Pick<DocumentSummary, "tags" | "metadata">): string[] {
  const tags = new Set<string>();

  if (Array.isArray(doc.tags)) {
    for (const tag of doc.tags) {
      if (typeof tag === "string") {
        const cleaned = tag.trim();
        if (cleaned) {
          tags.add(cleaned);
        }
      }
    }
  }

  const metadataTags = (doc.metadata as Record<string, unknown>)?.tags;
  if (Array.isArray(metadataTags)) {
    for (const tag of metadataTags) {
      if (typeof tag === "string") {
        const cleaned = tag.trim();
        if (cleaned) {
          tags.add(cleaned);
        }
      }
    }
  } else if (typeof metadataTags === "string") {
    const cleaned = metadataTags.trim();
    if (cleaned) {
      tags.add(cleaned);
    }
  }

  return Array.from(tags);
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

type PageProps = {
  params: {
    id: string;
  };
};

export default function DocumentsPage({ params }: PageProps) {
  const workspaceId = params.id;
  const searchParams = useSearchParams();
  const preferredDocId = searchParams.get("doc");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [draft, setDraft] = useState<UploadDraft>(emptyUpload);
  const [file, setFile] = useState<File | null>(null);
  const [dropActive, setDropActive] = useState(false);
  const [queryInput, setQueryInput] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [query, setQuery] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [sort, setSort] = useState<DocumentSort>("created_at_desc");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [apiKey, setApiKey] = useState("");

  const isAdmin = user?.role === "admin" || (!user && Boolean(apiKey));
  const isEmployee = user?.role === "employee";

  const activeFilters = useMemo(
    () => ({
      q: query || undefined,
      status: statusFilter === "ALL" ? undefined : statusFilter,
      tag: tagFilter || undefined,
      sort,
    }),
    [query, sort, statusFilter, tagFilter]
  );

  const loadDocuments = useCallback(
    async ({
      preferredId,
      cursor,
      append = false,
    }: {
      preferredId?: string | null;
      cursor?: string | null;
      append?: boolean;
    } = {}) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoadingList(true);
      }
      setError("");
      try {
        const res = await listWorkspaceDocuments(workspaceId, {
          ...activeFilters,
          cursor: cursor ?? undefined,
          limit: PAGE_SIZE,
        });
        setNextCursor(res.next_cursor ?? null);
        if (append) {
          setDocuments((prev) => [...prev, ...res.documents]);
          setSelectedId(
            (current) => current ?? res.documents[0]?.id ?? null
          );
        } else {
          setDocuments(res.documents);
          setSelectedId((current) => {
            const candidateId = preferredId ?? current;
            if (!res.documents.length) {
              return null;
            }
            if (candidateId && res.documents.some((doc) => doc.id === candidateId)) {
              return candidateId;
            }
            return res.documents[0].id;
          });
          setRefreshTick((prev) => prev + 1);
        }
      } catch (err) {
        setError(formatError(err));
      } finally {
        if (append) {
          setLoadingMore(false);
        } else {
          setLoadingList(false);
        }
      }
    },
    [activeFilters, workspaceId]
  );

  const loadDetail = useCallback(async (documentId: string) => {
    setLoadingDetail(true);
    setError("");
    try {
      const doc = await getWorkspaceDocument(workspaceId, documentId);
      setSelected(doc);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoadingDetail(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadDocuments({ preferredId: preferredDocId ?? undefined });
  }, [loadDocuments, preferredDocId]);

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
    return Object.entries(selected.metadata).filter(([key]) => key !== "tags");
  }, [selected]);

  const selectedTags = useMemo(
    () => (selected ? normalizeTags(selected) : []),
    [selected]
  );

  const applyFilters = useCallback(() => {
    setQuery(queryInput.trim());
    setTagFilter(tagInput.trim());
  }, [queryInput, tagInput]);

  const clearFilters = useCallback(() => {
    setQueryInput("");
    setTagInput("");
    setQuery("");
    setTagFilter("");
    setStatusFilter("ALL");
    setSort("created_at_desc");
  }, []);

  const filtersActive = useMemo(
    () =>
      Boolean(query) ||
      Boolean(tagFilter) ||
      statusFilter !== "ALL" ||
      sort !== "created_at_desc",
    [query, sort, statusFilter, tagFilter]
  );

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
        const tags = draft.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter((tag) => Boolean(tag));
        if (tags.length) {
          formData.append("metadata", JSON.stringify({ tags }));
        }

        const result = await uploadWorkspaceDocument(workspaceId, formData);
        setNotice(`Archivo subido: ${result.file_name}. Procesando...`);
        setFile(null);
        setDraft(emptyUpload);
        setSelectedId(result.document_id);
        await loadDocuments({ preferredId: result.document_id });
      } catch (err) {
        setError(formatError(err));
      } finally {
        setUploading(false);
      }
    },
    [draft, file, loadDocuments, workspaceId]
  );

  const handleReprocess = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    setError("");
    setNotice("");
    setReprocessing(true);
    try {
      const res = await reprocessWorkspaceDocument(workspaceId, selectedId);
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
  }, [loadDocuments, selectedId, workspaceId]);

  const handleDelete = useCallback(async () => {
    if (!selectedId) {
      return;
    }
    const confirmed = window.confirm(
      "Eliminar este documento? Esta accion no se puede deshacer."
    );
    if (!confirmed) {
      return;
    }
    setError("");
    setNotice("");
    setDeleting(true);
    try {
      await deleteWorkspaceDocument(workspaceId, selectedId);
      setNotice("Documento eliminado.");
      setSelectedId(null);
      setSelected(null);
      setDocuments((prev) => prev.filter((doc) => doc.id !== selectedId));
      await loadDocuments();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setDeleting(false);
    }
  }, [loadDocuments, selectedId, workspaceId]);

  const handleLoadMore = useCallback(async () => {
    if (!nextCursor || loadingMore) {
      return;
    }
    await loadDocuments({ cursor: nextCursor, append: true });
  }, [loadDocuments, loadingMore, nextCursor]);

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
            <span
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60"
              data-testid="sources-workspace"
            >
              Workspace {workspaceId}
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
                <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                  Tags (opcional)
                  <input
                    value={draft.tags}
                    onChange={(event) =>
                      setDraft((prev) => ({
                        ...prev,
                        tags: event.target.value,
                      }))
                    }
                    data-testid="sources-tags-input"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                    placeholder="legal, finanzas"
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
                  {documents.length} fuentes {filtersActive ? "filtradas" : "activas"}.
                </p>
              </div>
              <button
                type="button"
                onClick={() => loadDocuments()}
                data-testid="sources-refresh"
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white"
              >
                {needsPolling ? "Actualizando..." : "Refrescar"}
              </button>
            </div>

            <div
              className="mt-6 space-y-4 rounded-2xl border border-white/10 bg-slate-950/40 p-4"
              data-testid="sources-filters"
            >
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  applyFilters();
                }}
                className="grid gap-3 md:grid-cols-[1.4fr_1fr_auto_auto]"
              >
                <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50">
                  Buscar
                  <input
                    value={queryInput}
                    onChange={(event) => setQueryInput(event.target.value)}
                    data-testid="sources-search-input"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                    placeholder="Titulo, source o archivo"
                  />
                </label>
                <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50">
                  Tag
                  <input
                    value={tagInput}
                    onChange={(event) => setTagInput(event.target.value)}
                    data-testid="sources-tag-input"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                    placeholder="comercial"
                  />
                </label>
                <button
                  type="submit"
                  data-testid="sources-apply-filters"
                  className="self-end rounded-full bg-cyan-500/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-950 transition hover:bg-cyan-400"
                >
                  Aplicar
                </button>
                <button
                  type="button"
                  onClick={clearFilters}
                  data-testid="sources-clear-filters"
                  className="self-end rounded-full border border-white/10 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/60 transition hover:border-cyan-300/50 hover:text-white"
                >
                  Limpiar
                </button>
              </form>

              <div className="flex flex-wrap items-center gap-2">
                {STATUS_FILTERS.map((option) => {
                  const active = statusFilter === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setStatusFilter(option.value)}
                      data-testid={`sources-status-${option.value.toLowerCase()}`}
                      className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] transition ${
                        active
                          ? "border-cyan-300/60 bg-cyan-400/10 text-cyan-100"
                          : "border-white/10 text-white/50 hover:border-cyan-300/30 hover:text-white"
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>

              <label className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.2em] text-white/50">
                Orden
                <select
                  value={sort}
                  onChange={(event) =>
                    setSort(event.target.value as DocumentSort)
                  }
                  data-testid="sources-sort-select"
                  className="rounded-full border border-white/10 bg-slate-950/50 px-3 py-1 text-xs text-white/70 focus:border-cyan-400/60 focus:outline-none"
                >
                  {SORT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
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
                  const tags = normalizeTags(doc);
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
                          {tags.length ? (
                            <div className="flex flex-wrap items-center gap-1">
                              {tags.slice(0, 3).map((tag) => (
                                <span
                                  key={tag}
                                  data-testid="source-tag"
                                  className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-white/50"
                                >
                                  {tag}
                                </span>
                              ))}
                              {tags.length > 3 ? (
                                <span className="text-[10px] text-white/40">
                                  +{tags.length - 3}
                                </span>
                              ) : null}
                            </div>
                          ) : null}
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
            {nextCursor ? (
              <div className="mt-4 flex justify-center">
                <button
                  type="button"
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  data-testid="sources-load-more"
                  className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white disabled:cursor-not-allowed disabled:text-white/40"
                >
                  {loadingMore ? "Cargando..." : "Mostrar mas"}
                </button>
              </div>
            ) : null}
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
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleReprocess}
                    disabled={
                      reprocessing || normalizeStatus(selected.status) === "PROCESSING"
                    }
                    data-testid="source-reprocess-button"
                    className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white disabled:cursor-not-allowed disabled:text-white/40"
                  >
                    {reprocessing ? "Reprocesando..." : "Reprocesar"}
                  </button>
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={deleting}
                    data-testid="source-delete-button"
                    className="rounded-full border border-rose-400/40 px-4 py-2 text-sm text-rose-100 transition hover:border-rose-300/60 hover:text-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {deleting ? "Eliminando..." : "Eliminar"}
                  </button>
                </div>
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
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40">
                    Tags
                  </p>
                  {selectedTags.length === 0 ? (
                    <p className="text-white/50" data-testid="source-detail-tags">
                      Sin tags.
                    </p>
                  ) : (
                    <div
                      className="flex flex-wrap gap-2"
                      data-testid="source-detail-tags"
                    >
                      {selectedTags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
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
