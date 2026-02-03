/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/documents/components/DocumentsScreen.tsx (Screen documentos)
===============================================================================
Responsabilidades:
  - Renderizar la gestion de documentos por workspace.
  - Permitir filtros, uploads, reprocesos y borrados.
  - Mostrar estados, errores y avisos de manera consistente.

Colaboradores:
  - shared/api (documentos + auth)
  - shared/ui/StatusBanner y NoticeBanner
  - utils/formatters
  - next/link
===============================================================================
*/
"use client";

import {
  deleteWorkspaceDocument,
  getCurrentUser,
  getWorkspaceDocument,
  listWorkspaceDocuments,
  reprocessWorkspaceDocument,
  uploadWorkspaceDocument,
  type CurrentUser,
  type DocumentDetail,
  type DocumentSort,
  type DocumentStatus,
  type DocumentSummary,
} from "@/shared/api/api";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import { NoticeBanner } from "@/shared/ui/NoticeBanner";
import { StatusBanner } from "@/shared/ui/StatusBanner";
import { formatDate, formatError } from "@/utils/formatters";
import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";

type DocumentsScreenProps = {
  workspaceId?: string;
  preferredDocumentId?: string | null;
};

type WorkspaceDocumentsScreenProps = {
  workspaceId: string;
  preferredDocumentId?: string | null;
};

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
  PENDING: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  PROCESSING: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  READY: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  FAILED: "border-rose-500/30 bg-rose-500/10 text-rose-200",
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

export function DocumentsScreen({
  workspaceId,
  preferredDocumentId,
}: DocumentsScreenProps) {
  if (!workspaceId) {
    return <DocumentsEmptyState />;
  }

  return (
    <WorkspaceDocumentsScreen
      workspaceId={workspaceId}
      preferredDocumentId={preferredDocumentId}
    />
  );
}

function DocumentsEmptyState() {
  return (
    <section className="space-y-6">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <h1 className="text-2xl font-semibold text-white">Sources</h1>
        <p className="mt-2 text-sm text-white/60">
          Selecciona un workspace para administrar documentos.
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

function WorkspaceDocumentsScreen({
  workspaceId,
  preferredDocumentId,
}: WorkspaceDocumentsScreenProps) {
  const preferredId = useMemo(() => {
    if (!preferredDocumentId) {
      return undefined;
    }
    const trimmed = preferredDocumentId.trim();
    return trimmed ? trimmed : undefined;
  }, [preferredDocumentId]);

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
      preferredId: preferred,
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
          setSelectedId((current) => current ?? res.documents[0]?.id ?? null);
        } else {
          setDocuments(res.documents);
          setSelectedId((current) => {
            const candidateId = preferred ?? current;
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

  const loadDetail = useCallback(
    async (documentId: string) => {
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
    },
    [workspaceId]
  );

  useEffect(() => {
    void loadDocuments({ preferredId });
  }, [loadDocuments, preferredId]);

  useEffect(() => {
    setApiKey(getStoredApiKey());
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    void loadDetail(selectedId);
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
      void loadDocuments();
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

  const handleFileSelection = useCallback((nextFile: File | null) => {
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
  }, []);

  const handleFileInput = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const nextFile = event.target.files?.[0] ?? null;
      handleFileSelection(nextFile);
    },
    [handleFileSelection]
  );

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDropActive(false);
      const nextFile = event.dataTransfer.files?.[0] ?? null;
      handleFileSelection(nextFile);
    },
    [handleFileSelection]
  );

  const handleUpload = useCallback(
    async (event: FormEvent) => {
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
    <div className="space-y-8">
      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold sm:text-4xl text-white drop-shadow-sm">
            Sources
          </h1>
          <span
            className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200 font-bold shadow-sm"
            data-testid="sources-role"
          >
            {roleLabel}
          </span>
          <span
            className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/50 font-bold"
            data-testid="sources-workspace"
          >
            Workspace {workspaceId}
          </span>
        </div>
        <p className="max-w-2xl text-sm text-white/60 sm:text-base font-medium">
          Administra tus fuentes como en NotebookLM: sube PDFs/DOCX y monitorea
          el estado del procesamiento.
        </p>
      </section>

      <StatusBanner message={error} />
      <NoticeBanner message={notice} />

      {isAdmin ? (
        <section
          className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl backdrop-blur-md"
          data-testid="sources-upload-panel"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Subir fuente</h2>
              <p className="text-sm text-white/50">
                PDF o DOCX. El procesamiento corre en background.
              </p>
            </div>
            <div className="text-xs font-bold text-cyan-200 bg-cyan-950/50 border border-cyan-900 px-3 py-1 rounded-full">
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
                  ? "border-cyan-400 bg-cyan-400/10"
                  : "border-white/10 bg-black/20 hover:bg-black/30"
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
                className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:border-cyan-400 hover:text-cyan-400 cursor-pointer"
              >
                Elegir archivo
              </label>
              <p className="text-xs text-white/40">o arrastra y suelta aqui</p>
              {file ? (
                <div className="mt-3 space-y-1 text-sm text-white">
                  <p className="font-semibold">{file.name}</p>
                  <p className="text-xs text-white/50">
                    {file.type || "Tipo desconocido"} - {formatFileSize(file.size)}
                  </p>
                  <button
                    type="button"
                    onClick={clearFile}
                    className="text-xs text-rose-400 hover:text-rose-300 font-bold"
                    data-testid="sources-clear-file"
                  >
                    Quitar archivo
                  </button>
                </div>
              ) : null}
            </div>

            <div className="space-y-4">
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
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
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-sm transition-all"
                  placeholder="Guia comercial 2025"
                />
              </label>
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
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
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-sm transition-all"
                  placeholder="https://docs.example.com"
                />
              </label>
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
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
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-sm transition-all"
                  placeholder="legal, finanzas"
                />
              </label>

              <button
                type="submit"
                disabled={uploading || !file}
                data-testid="sources-upload-submit"
                className="flex w-full items-center justify-center gap-2 rounded-full bg-cyan-400 text-slate-950 px-6 py-2 text-sm font-bold shadow-lg shadow-cyan-400/20 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/30 disabled:shadow-none"
              >
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-900 border-t-transparent" />
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
        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md">
          <h2 className="text-lg font-bold text-white">Sources (solo lectura)</h2>
          <p className="text-sm text-white/50">
            Tu rol no permite cargar ni reprocesar archivos.
          </p>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Listado</h2>
              <p className="text-sm text-white/50">
                {documents.length} fuentes {filtersActive ? "filtradas" : "activas"}.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void loadDocuments()}
              data-testid="sources-refresh"
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/70 transition hover:border-cyan-300 hover:text-cyan-300 hover:shadow-sm"
            >
              {needsPolling ? "Actualizando..." : "Refrescar"}
            </button>
          </div>

          <div
            className="mt-6 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4"
            data-testid="sources-filters"
          >
            <form
              onSubmit={(event) => {
                event.preventDefault();
                applyFilters();
              }}
              className="grid gap-3 md:grid-cols-[1.4fr_1fr_auto_auto]"
            >
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
                Buscar
                <input
                  value={queryInput}
                  onChange={(event) => setQueryInput(event.target.value)}
                  data-testid="sources-search-input"
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                  placeholder="Titulo, source o archivo"
                />
              </label>
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
                Tag
                <input
                  value={tagInput}
                  onChange={(event) => setTagInput(event.target.value)}
                  data-testid="sources-tag-input"
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                  placeholder="comercial"
                />
              </label>
              <button
                type="submit"
                data-testid="sources-apply-filters"
                className="self-end rounded-full bg-cyan-400 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-950 transition hover:bg-cyan-300 shadow-md shadow-cyan-400/20"
              >
                Aplicar
              </button>
              <button
                type="button"
                onClick={clearFilters}
                data-testid="sources-clear-filters"
                className="self-end rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold transition hover:border-rose-300 hover:text-rose-300"
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
                    className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-bold transition ${
                      active
                        ? "border-cyan-400 bg-cyan-400/10 text-cyan-200"
                        : "border-white/10 bg-white/5 text-white/40 hover:border-cyan-200 hover:text-cyan-200"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {SORT_OPTIONS.map((option) => {
                const active = sort === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSort(option.value)}
                    data-testid={`sources-sort-${option.value}`}
                    className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-bold transition ${
                      active
                        ? "border-cyan-400 bg-cyan-400/10 text-cyan-200"
                        : "border-white/10 bg-white/5 text-white/40 hover:border-cyan-200 hover:text-cyan-200"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-6 space-y-4" data-testid="sources-list">
            {loadingList ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-white/40">
                Cargando documentos...
              </div>
            ) : documents.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">
                No hay documentos para mostrar.
              </div>
            ) : (
              documents.map((doc) => {
                const status = normalizeStatus(doc.status);
                const selectedClass = selectedId === doc.id;

                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => setSelectedId(doc.id)}
                    data-testid={`sources-item-${doc.id}`}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      selectedClass
                        ? "border-cyan-400/40 bg-cyan-500/10"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">
                          {doc.title || doc.file_name || "Documento sin titulo"}
                        </p>
                        <p className="text-xs text-white/40">
                          {doc.source || doc.file_name || "Sin fuente"}
                        </p>
                      </div>
                      <span
                        className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-bold ${
                          STATUS_STYLES[status]
                        }`}
                      >
                        {STATUS_LABELS[status]}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-white/40">
                      <span>{formatDate(doc.created_at)}</span>
                      {doc.tags?.length ? (
                        <span>{doc.tags.slice(0, 2).join(", ")}</span>
                      ) : null}
                    </div>
                  </button>
                );
              })
            )}
            {nextCursor ? (
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={loadingMore}
                data-testid="sources-load-more"
                className="w-full rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/60 transition hover:border-cyan-300 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loadingMore ? "Cargando..." : "Cargar mas"}
              </button>
            ) : null}
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Detalle</h2>
              <p className="text-sm text-white/50">
                {selectedId ? "Documento seleccionado" : "Selecciona un documento"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selectedId && isAdmin ? (
                <button
                  type="button"
                  onClick={handleReprocess}
                  disabled={reprocessing}
                  data-testid="sources-reprocess"
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-white/60 transition hover:border-cyan-300 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {reprocessing ? "Reprocesando..." : "Reprocesar"}
                </button>
              ) : null}
              {selectedId && isAdmin ? (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  data-testid="sources-delete"
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-white/60 transition hover:border-rose-300 hover:text-rose-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deleting ? "Eliminando..." : "Eliminar"}
                </button>
              ) : null}
            </div>
          </div>

          {loadingDetail ? (
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-white/40">
              Cargando detalle...
            </div>
          ) : !selected ? (
            <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-center text-sm text-white/40">
              Selecciona un documento para ver el detalle.
            </div>
          ) : (
            <div className="mt-6 space-y-6">
              <div className="space-y-2">
                <h3 className="text-lg font-bold text-white">
                  {selected.title || selected.file_name || "Documento sin titulo"}
                </h3>
                <p className="text-xs text-white/40 font-mono">{selected.id}</p>
                <p className="text-sm text-white/60">
                  {selected.source || "Sin fuente"}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  {(selectedTags.length ? selectedTags : []).map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60 font-bold"
                    >
                      {tag}
                    </span>
                  ))}
                  {!selectedTags.length ? (
                    <span className="text-xs text-white/40">Sin tags</span>
                  ) : null}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-white/40 font-bold">
                  Metadata
                </p>
                <div className="mt-3 space-y-2 text-xs text-white/60">
                  <div>
                    <span className="text-white/40">Estado: </span>
                    <span>{normalizeStatus(selected.status)}</span>
                  </div>
                  <div>
                    <span className="text-white/40">Creado: </span>
                    <span>{formatDate(selected.created_at)}</span>
                  </div>
                  {metadataEntries.length ? (
                    metadataEntries.map(([key, value]) => (
                      <div key={key}>
                        <span className="text-white/40">{key}: </span>
                        <span>{String(value)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-white/40">Sin metadata extra.</div>
                  )}
                </div>
              </div>

              {selected.content ? (
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                  <p className="text-xs uppercase tracking-[0.2em] text-white/40 font-bold">
                    Preview
                  </p>
                  <p className="mt-3 whitespace-pre-wrap">
                    {selected.content}
                  </p>
                </div>
              ) : null}

              {isEmployee ? (
                <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-xs text-amber-100">
                  Tu rol es de solo lectura. Para subir o reprocesar, solicita
                  permisos admin.
                </div>
              ) : null}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
