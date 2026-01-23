"use client";

import {
    archiveWorkspace,
    createWorkspace,
    getCurrentUser,
    listWorkspaces,
    publishWorkspace,
    shareWorkspace,
    type CurrentUser,
    type WorkspaceSummary,
} from "@/shared/api/api";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import { AppShell } from "@/shared/ui/AppShell";
import { NoticeBanner } from "@/shared/ui/NoticeBanner";
import { StatusBanner } from "@/shared/ui/StatusBanner";
import { WorkspaceVisibility } from "@contracts/src/generated";
import { useCallback, useEffect, useMemo, useState } from "react";

type WorkspaceDraft = {
  name: string;
  visibility: typeof WorkspaceVisibility[keyof typeof WorkspaceVisibility];
};

const emptyDraft: WorkspaceDraft = {
  name: "",
  visibility: WorkspaceVisibility.PRIVATE,
};

const VISIBILITY_LABELS: Record<WorkspaceDraft["visibility"], string> = {
  [WorkspaceVisibility.PRIVATE]: "Privado",
  [WorkspaceVisibility.ORG_READ]: "Org Read",
  [WorkspaceVisibility.SHARED]: "Compartido",
};

const VISIBILITY_STYLES: Record<WorkspaceDraft["visibility"], string> = {
  [WorkspaceVisibility.PRIVATE]: "border-slate-400/40 bg-slate-400/10 text-slate-200",
  [WorkspaceVisibility.ORG_READ]: "border-cyan-400/40 bg-cyan-400/10 text-cyan-100",
  [WorkspaceVisibility.SHARED]: "border-amber-400/40 bg-amber-400/10 text-amber-100",
};

const VISIBILITY_OPTIONS: Array<{ value: WorkspaceDraft["visibility"]; label: string }> = [
  { value: WorkspaceVisibility.PRIVATE, label: "Privado" },
  { value: WorkspaceVisibility.ORG_READ, label: "Org Read" },
  { value: WorkspaceVisibility.SHARED, label: "Compartido" },
];

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

function isArchived(workspace: WorkspaceSummary): boolean {
  return Boolean(workspace.archived_at);
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [draft, setDraft] = useState<WorkspaceDraft>(emptyDraft);
  const [shareDrafts, setShareDrafts] = useState<Record<string, string>>({});
  const [shareOpenId, setShareOpenId] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [apiKey, setApiKey] = useState("");

  const isAdmin = user?.role === "admin" || (!user && Boolean(apiKey));
  const canCreate = isAdmin || user?.role === "employee";

  const roleLabel = useMemo(() => {
    if (!authChecked) {
      return "Verificando";
    }
    if (user) {
      return user.role === "admin" ? "Admin" : "Empleado";
    }
    if (apiKey) {
      return "API Key";
    }
    return "Sin sesion";
  }, [apiKey, authChecked, user]);

  const loadWorkspaces = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listWorkspaces({ includeArchived });
      setWorkspaces(res.workspaces);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  }, [includeArchived]);

  useEffect(() => {
    setApiKey(getStoredApiKey());
    let active = true;
    getCurrentUser()
      .then((current) => {
        if (active) {
          setUser(current);
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

  useEffect(() => {
    if (authChecked) {
      loadWorkspaces();
    }
  }, [authChecked, loadWorkspaces]);

  const updateWorkspace = useCallback((updated: WorkspaceSummary) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === updated.id ? updated : workspace
      )
    );
  }, []);

  const handleCreate = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setError("");
      setNotice("");

      const trimmedName = draft.name.trim();
      if (!trimmedName) {
        setError("El nombre del workspace es obligatorio.");
        return;
      }

      setCreating(true);
      try {
        const created = await createWorkspace({
          name: trimmedName,
          visibility: draft.visibility,
        });
        setWorkspaces((prev) => [created, ...prev]);
        setDraft(emptyDraft);
        setNotice(`Workspace creado: ${created.name}`);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setCreating(false);
      }
    },
    [draft]
  );

  const handlePublish = useCallback(
    async (workspace: WorkspaceSummary) => {
      setWorkingId(workspace.id);
      setError("");
      setNotice("");
      try {
        const updated = await publishWorkspace(workspace.id);
        updateWorkspace(updated);
        setNotice(`Workspace publicado: ${updated.name}`);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setWorkingId(null);
      }
    },
    [updateWorkspace]
  );

  const handleShare = useCallback(
    async (workspace: WorkspaceSummary) => {
      const raw = shareDrafts[workspace.id] || "";
      const userIds = raw
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean);

      if (!userIds.length) {
        setError("Ingresa al menos un user_id para compartir.");
        return;
      }

      setWorkingId(workspace.id);
      setError("");
      setNotice("");
      try {
        const updated = await shareWorkspace(workspace.id, { user_ids: userIds });
        updateWorkspace(updated);
        setShareDrafts((prev) => ({ ...prev, [workspace.id]: "" }));
        setNotice(`Workspace compartido: ${updated.name}`);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setWorkingId(null);
      }
    },
    [shareDrafts, updateWorkspace]
  );

  const handleArchive = useCallback(
    async (workspace: WorkspaceSummary) => {
      const confirmed = window.confirm(
        `Archivar "${workspace.name}"? No estara visible por defecto.`
      );
      if (!confirmed) {
        return;
      }
      setWorkingId(workspace.id);
      setError("");
      setNotice("");
      try {
        const result = await archiveWorkspace(workspace.id);
        if (result.archived) {
          await loadWorkspaces();
          setNotice(`Workspace archivado: ${workspace.name}`);
        }
      } catch (err) {
        setError(formatError(err));
      } finally {
        setWorkingId(null);
      }
    },
    [loadWorkspaces]
  );

  return (
    <AppShell>
      <div className="space-y-8" data-testid="workspaces-page">
        <section className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold sm:text-4xl">Workspaces</h1>
            <span
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/60"
              data-testid="workspaces-role"
            >
              {roleLabel}
            </span>
          </div>
          <p className="max-w-2xl text-sm text-white/60 sm:text-base">
            Gestiona visibilidad y acceso. Publica a toda la organizacion, comparte
            con usuarios puntuales o archiva cuando ya no sea necesario.
          </p>
        </section>

        <StatusBanner message={error} />
        <NoticeBanner message={notice} />

        {canCreate ? (
          <section
            className="rounded-3xl border border-white/10 bg-white/5 p-6"
            data-testid="workspaces-create-panel"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Crear workspace</h2>
                <p className="text-sm text-white/60">
                  Por defecto queda en privado hasta publicar o compartir.
                </p>
              </div>
              <div className="text-xs text-white/50">
                {workspaces.length} activos
              </div>
            </div>

            <form
              onSubmit={handleCreate}
              className="mt-6 grid gap-4 md:grid-cols-[1.5fr_1fr_auto]"
              data-testid="workspaces-create-form"
            >
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                Nombre
                <input
                  value={draft.name}
                  onChange={(event) =>
                    setDraft((prev) => ({ ...prev, name: event.target.value }))
                  }
                  data-testid="workspaces-create-name"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                  placeholder="Legal Ops"
                />
              </label>
              <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                Visibilidad
                <select
                  value={draft.visibility}
                  onChange={(event) =>
                    setDraft((prev) => ({
                      ...prev,
                      visibility: event.target.value as WorkspaceDraft["visibility"],
                    }))
                  }
                  data-testid="workspaces-create-visibility"
                  className="w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white/70 focus:border-cyan-400/60 focus:outline-none"
                >
                  {VISIBILITY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                disabled={creating}
                data-testid="workspaces-create-submit"
                className="self-end rounded-full bg-cyan-500/80 px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-900/40 disabled:text-white/40"
              >
                {creating ? "Creando..." : "Crear"}
              </button>
            </form>
          </section>
        ) : (
          <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-lg font-semibold">Workspaces (solo lectura)</h2>
            <p className="text-sm text-white/60">
              Tu rol no permite crear ni administrar workspaces.
            </p>
          </section>
        )}

        <section
          className="rounded-3xl border border-white/10 bg-white/5 p-6"
          data-testid="workspaces-list-section"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Listado</h2>
              <p className="text-sm text-white/60">
                {workspaces.length} workspaces visibles.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-white/50">
                <input
                  type="checkbox"
                  checked={includeArchived}
                  onChange={(event) => setIncludeArchived(event.target.checked)}
                  data-testid="workspaces-include-archived"
                  className="h-4 w-4 rounded border-white/20 bg-white/10 text-cyan-400"
                />
                Incluir archivados
              </label>
              <button
                type="button"
                onClick={loadWorkspaces}
                data-testid="workspaces-refresh"
                className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/70 transition hover:border-cyan-300/50 hover:text-white"
              >
                Refrescar
              </button>
            </div>
          </div>

          <div
            className="mt-6 grid gap-4 md:grid-cols-2"
            data-testid="workspaces-list"
          >
            {loading ? (
              <p className="text-sm text-white/50">Cargando workspaces...</p>
            ) : workspaces.length ? (
              workspaces.map((workspace) => {
                const archived = isArchived(workspace);
                const canManage =
                  isAdmin ||
                  (user && workspace.owner_user_id && user.id === workspace.owner_user_id);
                const canPublish =
                  !archived && workspace.visibility === WorkspaceVisibility.PRIVATE;

                return (
                  <div
                    key={workspace.id}
                    className="rounded-2xl border border-white/10 bg-slate-950/40 p-5"
                    data-testid={`workspace-card-${workspace.id}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-white">
                          {workspace.name}
                        </h3>
                        <p className="mt-1 text-xs text-white/50">
                          ID: <span className="font-mono">{workspace.id}</span>
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span
                          className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] ${
                            VISIBILITY_STYLES[workspace.visibility]
                          }`}
                          data-testid={`workspace-visibility-${workspace.id}`}
                        >
                          {VISIBILITY_LABELS[workspace.visibility]}
                        </span>
                        {archived ? (
                          <span className="rounded-full border border-rose-400/40 bg-rose-400/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-rose-100">
                            Archivado
                          </span>
                        ) : null}
                      </div>
                    </div>

                    <div className="mt-4 space-y-1 text-xs text-white/50">
                      <p>Creado: {formatDate(workspace.created_at)}</p>
                      <p>
                        Owner: {workspace.owner_user_id ? (
                          <span className="font-mono">{workspace.owner_user_id}</span>
                        ) : (
                          "Sin owner"
                        )}
                      </p>
                      {workspace.acl?.allowed_roles?.length ? (
                        <p>Roles: {workspace.acl.allowed_roles.join(", ")}</p>
                      ) : null}
                    </div>

                    {canManage ? (
                      <div className="mt-4 flex flex-wrap items-center gap-2">
                        {canPublish ? (
                          <button
                            type="button"
                            onClick={() => handlePublish(workspace)}
                            disabled={workingId === workspace.id}
                            data-testid={`workspace-action-publish-${workspace.id}`}
                            className="rounded-full bg-cyan-500/80 px-3 py-1 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-900/40 disabled:text-white/40"
                          >
                            Publicar
                          </button>
                        ) : null}
                        {!archived ? (
                          <button
                            type="button"
                            onClick={() =>
                              setShareOpenId((prev) =>
                                prev === workspace.id ? null : workspace.id
                              )
                            }
                            disabled={workingId === workspace.id}
                            data-testid={`workspace-action-share-toggle-${workspace.id}`}
                            className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/70 transition hover:border-amber-300/50 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Compartir
                          </button>
                        ) : null}
                        {!archived ? (
                          <button
                            type="button"
                            onClick={() => handleArchive(workspace)}
                            disabled={workingId === workspace.id}
                            data-testid={`workspace-action-archive-${workspace.id}`}
                            className="rounded-full border border-rose-400/40 px-3 py-1 text-xs text-rose-100 transition hover:border-rose-300/60 hover:text-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Archivar
                          </button>
                        ) : null}
                      </div>
                    ) : (
                      <p className="mt-4 text-xs text-white/40">
                        Sin permisos para administrar este workspace.
                      </p>
                    )}

                    {shareOpenId === workspace.id && !archived ? (
                      <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
                        <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/60">
                          User IDs
                          <textarea
                            rows={2}
                            value={shareDrafts[workspace.id] ?? ""}
                            onChange={(event) =>
                              setShareDrafts((prev) => ({
                                ...prev,
                                [workspace.id]: event.target.value,
                              }))
                            }
                            data-testid={`workspace-share-input-${workspace.id}`}
                            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-amber-400/60 focus:outline-none focus:ring-2 focus:ring-amber-400/20"
                            placeholder="UUIDs separados por coma"
                          />
                        </label>
                        <div className="mt-3 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleShare(workspace)}
                            disabled={workingId === workspace.id}
                            data-testid={`workspace-share-submit-${workspace.id}`}
                            className="rounded-full bg-amber-400/80 px-4 py-1 text-xs font-semibold text-slate-900 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:bg-amber-900/30 disabled:text-white/40"
                          >
                            Guardar share
                          </button>
                          <button
                            type="button"
                            onClick={() => setShareOpenId(null)}
                            className="text-xs text-white/50 hover:text-white"
                            data-testid={`workspace-share-cancel-${workspace.id}`}
                          >
                            Cerrar
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })
            ) : (
              <div
                className="rounded-2xl border border-dashed border-white/10 bg-slate-950/40 p-8 text-center text-sm text-white/50"
                data-testid="workspaces-empty"
              >
                No hay workspaces todavia. Crea el primero para empezar.
              </div>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
