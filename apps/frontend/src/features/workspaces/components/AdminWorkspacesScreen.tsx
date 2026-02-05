/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/workspaces/components/AdminWorkspacesScreen.tsx (Screen admin workspaces)
===============================================================================
Responsabilidades:
  - Permitir a admins crear workspaces para usuarios.
  - Listar workspaces de un usuario seleccionado.
  - Mostrar estados de carga, error y confirmaciones.

Colaboradores:
  - shared/api (workspaces y usuarios)
  - shared/ui/components/StatusBanner y NoticeBanner
  - shared/lib/formatters
===============================================================================
*/
"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  adminCreateWorkspace,
  adminListWorkspaces,
  type AdminUser,
  type AdminWorkspaceSummary,
  type CurrentUser,
  getCurrentUser,
  listUsers,
} from "@/shared/api/api";
import { formatDate, formatError } from "@/shared/lib/formatters";
import { NoticeBanner } from "@/shared/ui/components/NoticeBanner";
import { StatusBanner } from "@/shared/ui/components/StatusBanner";

type WorkspaceDraft = {
  name: string;
  description: string;
};

const emptyDraft: WorkspaceDraft = {
  name: "",
  description: "",
};

export function AdminWorkspacesScreen() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceSummary[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [workspacesLoading, setWorkspacesLoading] = useState(false);

  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<WorkspaceDraft>(emptyDraft);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const isAdmin = currentUser?.role === "admin";

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((user) => {
        if (active) setCurrentUser(user);
      })
      .catch((err) => {
        if (active) setError(formatError(err));
      })
      .finally(() => {
        if (active) setAuthChecked(true);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!isAdmin) {
      return;
    }
    setUsersLoading(true);
    listUsers()
      .then((res) => setUsers(res.users))
      .catch((err) => setError(formatError(err)))
      .finally(() => setUsersLoading(false));
  }, [isAdmin]);

  useEffect(() => {
    if (selectedUserId && isAdmin) {
      setWorkspacesLoading(true);
      adminListWorkspaces(selectedUserId)
        .then((res) => setWorkspaces(res.workspaces))
        .catch((err) => setError(formatError(err)))
        .finally(() => setWorkspacesLoading(false));
    } else {
      setWorkspaces([]);
    }
  }, [selectedUserId, isAdmin]);

  const handleCreate = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      setError("");
      setNotice("");

      if (!selectedUserId) {
        setError("Selecciona un usuario primero.");
        return;
      }

      const trimmedName = draft.name.trim();
      if (!trimmedName) {
        setError("El nombre del workspace es obligatorio.");
        return;
      }

      setCreating(true);
      try {
        const created = await adminCreateWorkspace({
          owner_user_id: selectedUserId,
          name: trimmedName,
          description: draft.description || undefined,
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
    [draft, selectedUserId]
  );

  return (
    <section className="space-y-8">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.3em] text-white/40">
            Admin
          </p>
          <h1 className="text-3xl font-semibold text-white">
            Workspaces Provisioning
          </h1>
          <p className="text-sm text-white/60">
            Crea workspaces directamente para cualquier usuario de la
            organizacion.
          </p>
        </div>
      </div>

      <StatusBanner message={error} />
      <NoticeBanner message={notice} />

      {authChecked && !isAdmin ? (
        <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-6 text-rose-100">
          Acceso restringido. Necesitas un usuario admin para aprovisionar
          workspaces.
        </div>
      ) : (
        <div className="grid gap-8 lg:grid-cols-[1fr,2fr]">
          <div className="space-y-6">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <h2 className="mb-4 text-lg font-bold text-white">
                1. Seleccionar Usuario
              </h2>
              {usersLoading ? (
                <p className="text-sm text-white/40">Cargando usuarios...</p>
              ) : (
                <select
                  data-testid="admin-workspaces-user-select"
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400/20"
                >
                  <option value="">-- Selecciona un usuario --</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.email} ({u.role})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 opacity-100 transition-opacity">
              <h2 className="mb-4 text-lg font-bold text-white">
                2. Crear Workspace
              </h2>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
                    Nombre
                  </label>
                  <input
                    data-testid="admin-workspaces-name-input"
                    value={draft.name}
                    onChange={(e) =>
                      setDraft((prev) => ({ ...prev, name: e.target.value }))
                    }
                    disabled={!selectedUserId}
                    placeholder="Marketing Q1"
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/30 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400/20 disabled:opacity-50"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.2em] text-white/50 font-bold">
                    Descripcion (Opcional)
                  </label>
                  <input
                    value={draft.description}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                    disabled={!selectedUserId}
                    placeholder="Workspace para campanas..."
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-white/30 focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400/20 disabled:opacity-50"
                  />
                </div>

                <button
                  data-testid="admin-workspaces-submit"
                  type="submit"
                  disabled={creating || !selectedUserId || !draft.name.trim()}
                  className="w-full rounded-full bg-rose-500/10 border border-rose-500/20 px-4 py-2 text-sm font-bold text-rose-200 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {creating ? "Creando..." : "Crear Workspace"}
                </button>
              </form>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 min-h-[400px]">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">
                Workspaces del Usuario
              </h2>
              {selectedUserId && (
                <span className="text-xs font-mono text-white/40">
                  ID: {selectedUserId.substring(0, 8)}...
                </span>
              )}
            </div>

            {!selectedUserId ? (
              <div className="flex h-64 items-center justify-center text-white/30 text-sm">
                Selecciona un usuario para ver sus workspaces.
              </div>
            ) : workspacesLoading ? (
              <div className="flex h-64 items-center justify-center text-white/30 text-sm">
                Cargando workspaces...
              </div>
            ) : workspaces.length === 0 ? (
              <div className="flex h-64 items-center justify-center text-white/30 text-sm flex-col gap-2">
                <p>Este usuario no tiene workspaces.</p>
                <p className="text-xs">Usa el formulario para crear uno.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {workspaces.map((ws) => (
                  <div
                    key={ws.id}
                    className="rounded-xl border border-white/5 bg-black/20 p-4 transition hover:border-white/10"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-bold text-white text-sm">{ws.name}</h3>
                        <p className="text-xs text-white/40 font-mono mt-1">
                          {ws.id}
                        </p>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                          ws.visibility === "PRIVATE"
                            ? "bg-white/5 text-white/50"
                            : ws.visibility === "ORG_READ"
                              ? "bg-cyan-500/10 text-cyan-200"
                              : "bg-amber-500/10 text-amber-200"
                        }`}
                      >
                        {ws.visibility}
                      </span>
                    </div>
                    <div className="mt-3 flex gap-4 text-xs text-white/40">
                      <span>Creado: {formatDate(ws.created_at)}</span>
                      {ws.archived_at && (
                        <span className="text-rose-300">Archivado</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
