/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/workspaces/components/WorkspacesScreen.tsx (Screen workspaces)
===============================================================================
Responsabilidades:
  - Listar workspaces visibles y permitir acciones de administracion.
  - Crear, publicar, compartir y archivar workspaces cuando el rol lo permite.
  - Mantener feedback de estado y errores para el usuario.

Colaboradores:
  - shared/api (workspaces + auth)
  - shared/ui/components/StatusBanner y NoticeBanner
  - shared/lib/formatters
===============================================================================
*/
"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  archiveWorkspace,
  createWorkspace,
  type CurrentUser,
  getCurrentUser,
  listWorkspaces,
  publishWorkspace,
  shareWorkspace,
  type WorkspaceSummary,
} from "@/shared/api/api";
import { WorkspaceVisibility } from "@/shared/api/contracts/workspaces";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import { formatDate, formatError } from "@/shared/lib/formatters";
import { NoticeBanner } from "@/shared/ui/components/NoticeBanner";
import { StatusBanner } from "@/shared/ui/components/StatusBanner";

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

const VISIBILITY_OPTIONS: Array<{
  value: WorkspaceDraft["visibility"];
  label: string;
}> = [
  { value: WorkspaceVisibility.PRIVATE, label: "Privado" },
  { value: WorkspaceVisibility.ORG_READ, label: "Org Read" },
  { value: WorkspaceVisibility.SHARED, label: "Compartido" },
];

function isArchived(workspace: WorkspaceSummary): boolean {
  return Boolean(workspace.archived_at);
}

export function WorkspacesScreen() {
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

  const isAdmin = user?.role?.toLowerCase() === "admin";
  const canCreate = isAdmin;

  const roleLabel = useMemo(() => {
    if (!authChecked) {
      return "Verificando";
    }
    if (user) {
      return user.role?.toLowerCase() === "admin" ? "Admin" : "Empleado";
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
      void loadWorkspaces();
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
    async (event: FormEvent) => {
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
    <div className="space-y-8" data-testid="workspaces-page">
      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold sm:text-4xl text-white drop-shadow-sm">
            Workspaces
          </h1>
          <span
            className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200 font-bold shadow-sm"
            data-testid="workspaces-role"
          >
            {roleLabel}
          </span>
        </div>
        <p className="max-w-2xl text-sm text-white/60 sm:text-base font-medium">
          Gestiona visibilidad y acceso. Publica a toda la organizacion, comparte
          con usuarios puntuales o archiva cuando ya no sea necesario.
        </p>
      </section>

      <StatusBanner message={error} />
      <NoticeBanner message={notice} />

      {canCreate ? (
        <section
          className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl backdrop-blur-md"
          data-testid="workspaces-create-panel"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Crear workspace</h2>
              <p className="text-sm text-white/50">
                Por defecto queda en privado hasta publicar o compartir.
              </p>
            </div>
            <div className="text-xs font-bold text-cyan-200 bg-cyan-950/50 border border-cyan-900 px-3 py-1 rounded-full">
              {workspaces.length} activos
            </div>
          </div>

          <form
            onSubmit={handleCreate}
            className="mt-6 grid gap-4 md:grid-cols-[1.5fr_1fr_auto]"
            data-testid="workspaces-create-form"
          >
            <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
              Nombre
              <input
                value={draft.name}
                onChange={(event) =>
                  setDraft((prev) => ({ ...prev, name: event.target.value }))
                }
                data-testid="workspaces-create-name"
                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-sm transition-all"
                placeholder="Legal Ops"
              />
            </label>
            <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
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
                className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2.5 text-sm text-white/80 focus:border-cyan-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/10 shadow-sm transition-all"
              >
                {VISIBILITY_OPTIONS.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    className="bg-zinc-900 text-white"
                  >
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              disabled={creating}
              data-testid="workspaces-create-submit"
              className="self-end rounded-full bg-cyan-400 px-6 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-400/20 transition hover:bg-cyan-300 hover:shadow-cyan-300/30 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/30 disabled:shadow-none"
            >
              {creating ? "Creando..." : "Crear"}
            </button>
          </form>
        </section>
      ) : (
        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md">
          <h2 className="text-lg font-bold text-white">
            Workspaces (solo lectura)
          </h2>
          <p className="text-sm text-white/50">
            Tu rol no permite crear ni administrar workspaces.
          </p>
        </section>
      )}

      <section
        className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md"
        data-testid="workspaces-list-section"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Listado</h2>
            <p className="text-sm text-white/50">
              {workspaces.length} workspaces visibles.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-white/50 font-bold cursor-pointer hover:text-cyan-400 transition-colors">
              <input
                type="checkbox"
                checked={includeArchived}
                onChange={(event) => setIncludeArchived(event.target.checked)}
                data-testid="workspaces-include-archived"
                className="h-4 w-4 rounded border-white/20 bg-white/5 text-cyan-400 focus:ring-cyan-400 focus:ring-offset-0"
              />
              Incluir archivados
            </label>
            <button
              type="button"
              onClick={loadWorkspaces}
              data-testid="workspaces-refresh"
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/70 transition hover:border-cyan-300 hover:text-cyan-300 hover:shadow-sm"
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
            <p className="text-sm text-white/30">Cargando workspaces...</p>
          ) : workspaces.length ? (
            workspaces.map((workspace) => {
              const archived = isArchived(workspace);
              const canManage = isAdmin;
              const canPublish =
                !archived && workspace.visibility === WorkspaceVisibility.PRIVATE;

              return (
                <div
                  key={workspace.id}
                  className="group rounded-2xl border border-white/10 bg-white/5 p-5 shadow-sm transition-all hover:shadow-md hover:bg-white/10 hover:border-white/20"
                  data-testid={`workspace-card-${workspace.id}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                        {workspace.name}
                      </h3>
                      <p className="mt-1 text-xs text-white/30 font-mono">
                        ID: {workspace.id.substring(0, 8)}...
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span
                        className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-bold ${
                          workspace.visibility === WorkspaceVisibility.PRIVATE
                            ? "border-white/10 bg-white/5 text-white/50"
                            : workspace.visibility === WorkspaceVisibility.ORG_READ
                              ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
                              : "border-amber-500/30 bg-amber-500/10 text-amber-200"
                        }`}
                        data-testid={`workspace-visibility-${workspace.id}`}
                      >
                        {VISIBILITY_LABELS[workspace.visibility]}
                      </span>
                      {archived ? (
                        <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-bold text-rose-300">
                          Archivado
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-4 space-y-1 text-xs text-white/40">
                    <p>
                      Creado:{" "}
                      <span className="text-white/70">
                        {formatDate(workspace.created_at)}
                      </span>
                    </p>
                    <p>
                      Owner:{" "}
                      {workspace.owner_user_id ? (
                        <span className="font-mono text-white/70">
                          {workspace.owner_user_id.substring(0, 8)}...
                        </span>
                      ) : (
                        "Sin owner"
                      )}
                    </p>
                    {workspace.acl?.allowed_roles?.length ? (
                      <p>
                        Roles:{" "}
                        <span className="font-semibold text-white/60">
                          {workspace.acl.allowed_roles.join(", ")}
                        </span>
                      </p>
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
                          className="rounded-full bg-cyan-400/10 border border-cyan-400/20 px-3 py-1 text-xs font-bold text-cyan-200 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
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
                          className="rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-white/60 transition hover:border-amber-300/50 hover:text-amber-200 hover:bg-amber-500/10 disabled:cursor-not-allowed disabled:opacity-60"
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
                          className="rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-white/60 transition hover:border-rose-300/50 hover:text-rose-200 hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Archivar
                        </button>
                      ) : null}
                    </div>
                  ) : (
                    <p className="mt-4 text-xs italic text-white/30">
                      Sin permisos para administrar este workspace.
                    </p>
                  )}

                  {shareOpenId === workspace.id && !archived ? (
                    <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4 shadow-inner">
                      <label className="space-y-2 text-xs uppercase tracking-[0.2em] text-cyan-200/80 font-bold">
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
                          className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/20 focus:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-400/20"
                          placeholder="UUIDs separados por coma"
                        />
                      </label>
                      <div className="mt-3 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleShare(workspace)}
                          disabled={workingId === workspace.id}
                          data-testid={`workspace-share-submit-${workspace.id}`}
                          className="rounded-full bg-amber-500 px-4 py-1.5 text-xs font-bold text-white shadow-md shadow-amber-500/20 transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Guardar share
                        </button>
                        <button
                          type="button"
                          onClick={() => setShareOpenId(null)}
                          className="text-xs font-medium text-white/40 hover:text-white"
                          data-testid={`workspace-share-cancel-${workspace.id}`}
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })
          ) : (
            <div
              className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-10 text-center text-sm text-white/40"
              data-testid="workspaces-empty"
            >
              {canCreate
                ? "No hay workspaces todavia. Crea el primero para empezar."
                : "No tienes workspaces asignados. Contacta a un administrador para obtener acceso."}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
