/**
===============================================================================
TARJETA CRC - apps/frontend/src/features/auth/components/AdminUsersScreen.tsx (Screen admin usuarios)
===============================================================================
Responsabilidades:
  - Gestionar usuarios del portal admin (alta, baja, reset).
  - Coordinar carga de usuarios y estado de formularios.
  - Mostrar feedback de errores y confirmaciones.

Colaboradores:
  - shared/api (auth y usuarios)
  - shared/ui/StatusBanner y NoticeBanner
  - utils/formatters
===============================================================================
*/
"use client";

import {
  createUser,
  disableUser,
  getCurrentUser,
  listUsers,
  resetUserPassword,
  type AdminUser,
  type CreateUserPayload,
  type CurrentUser,
} from "@/shared/api/api";
import { NoticeBanner } from "@/shared/ui/NoticeBanner";
import { StatusBanner } from "@/shared/ui/StatusBanner";
import { formatDate, formatError } from "@/utils/formatters";
import { useCallback, useEffect, useState, type FormEvent } from "react";

type DraftUser = {
  email: string;
  password: string;
  role: "admin" | "employee";
};

const emptyDraft: DraftUser = {
  email: "",
  password: "",
  role: "employee",
};

export function AdminUsersScreen() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftUser>(emptyDraft);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const isAdmin = currentUser?.role === "admin";

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listUsers();
      setUsers(res.users);
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((user) => {
        if (active) {
          setCurrentUser(user);
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
    if (isAdmin) {
      void loadUsers();
    }
  }, [isAdmin, loadUsers]);

  const updateUser = useCallback((updated: AdminUser) => {
    setUsers((prev) =>
      prev.map((user) => (user.id === updated.id ? updated : user))
    );
  }, []);

  const handleCreate = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      setError("");
      setNotice("");

      const payload: CreateUserPayload = {
        email: draft.email.trim().toLowerCase(),
        password: draft.password,
        role: draft.role,
      };

      if (!payload.email || !payload.password) {
        setError("Email y password son obligatorios.");
        return;
      }

      setCreating(true);
      try {
        const created = await createUser(payload);
        setUsers((prev) => [created, ...prev]);
        setDraft(emptyDraft);
        setNotice(`Usuario creado: ${created.email}`);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setCreating(false);
      }
    },
    [draft]
  );

  const handleDisable = useCallback(
    async (user: AdminUser) => {
      if (!user.is_active) {
        return;
      }
      const confirmed = window.confirm(
        `Desactivar a ${user.email}? El usuario no podra iniciar sesion.`
      );
      if (!confirmed) {
        return;
      }
      setWorkingId(user.id);
      setError("");
      setNotice("");
      try {
        const updated = await disableUser(user.id);
        updateUser(updated);
        setNotice(`Usuario desactivado: ${updated.email}`);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setWorkingId(null);
      }
    },
    [updateUser]
  );

  const handleResetPassword = useCallback(
    async (user: AdminUser) => {
      const password = window.prompt(`Nuevo password para ${user.email}:`, "");
      if (!password) {
        return;
      }
      setWorkingId(user.id);
      setError("");
      setNotice("");
      try {
        const updated = await resetUserPassword(user.id, password);
        updateUser(updated);
        setNotice(`Password reseteado para ${updated.email}`);
      } catch (err) {
        setError(formatError(err));
      } finally {
        setWorkingId(null);
      }
    },
    [updateUser]
  );

  return (
    <section className="space-y-8">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.3em] text-white/40">
            Admin
          </p>
          <h1 className="text-3xl font-semibold text-white">Usuarios</h1>
          <p className="text-sm text-white/60">
            Gestiona cuentas internas: alta de empleados, baja y reset de
            password.
          </p>
        </div>
      </div>

      <StatusBanner message={error} />
      <NoticeBanner message={notice} />

      {authChecked && !isAdmin ? (
        <div
          className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-6 text-rose-100"
          data-testid="admin-users-denied"
        >
          Acceso restringido. Necesitas un usuario admin para administrar
          cuentas.
        </div>
      ) : (
        <>
          <form
            onSubmit={handleCreate}
            className="grid gap-4 rounded-3xl border border-white/10 bg-white/5 p-6 md:grid-cols-[2fr,2fr,1fr,auto]"
          >
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-[0.2em] text-white/50">
                Email
              </label>
              <input
                value={draft.email}
                onChange={(event) =>
                  setDraft((prev) => ({ ...prev, email: event.target.value }))
                }
                placeholder="empleado@ragcorp.com"
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-[0.2em] text-white/50">
                Password
              </label>
              <input
                type="password"
                value={draft.password}
                onChange={(event) =>
                  setDraft((prev) => ({
                    ...prev,
                    password: event.target.value,
                  }))
                }
                placeholder="Min 8 caracteres"
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-[0.2em] text-white/50">
                Rol
              </label>
              <select
                value={draft.role}
                onChange={(event) =>
                  setDraft((prev) => ({
                    ...prev,
                    role: event.target.value as DraftUser["role"],
                  }))
                }
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
              >
                <option value="employee">Empleado</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={creating || !isAdmin}
                className="inline-flex w-full items-center justify-center rounded-full border border-cyan-400/60 bg-cyan-400/20 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {creating ? "Creando..." : "Crear usuario"}
              </button>
            </div>
          </form>

          <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/5">
            <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
              <h2 className="text-lg font-semibold text-white">
                Usuarios registrados
              </h2>
              <span className="text-xs uppercase tracking-[0.2em] text-white/40">
                {loading ? "Cargando" : `${users.length} usuarios`}
              </span>
            </div>
            <div className="divide-y divide-white/5">
              {users.map((user) => (
                <div
                  key={user.id}
                  className="grid gap-4 px-6 py-4 md:grid-cols-[2fr,1fr,1fr,2fr]"
                  data-testid="admin-users-row"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-white">
                      {user.email}
                    </p>
                    <p className="text-xs text-white/40">{user.id}</p>
                  </div>
                  <div className="text-xs uppercase tracking-[0.2em] text-white/50">
                    {user.role}
                  </div>
                  <div className="text-sm text-white/60">
                    {user.is_active ? "Activo" : "Inactivo"}
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-white/50">
                    <span>{formatDate(user.created_at)}</span>
                    <button
                      type="button"
                      onClick={() => handleResetPassword(user)}
                      disabled={workingId === user.id || !isAdmin}
                      className="rounded-full border border-white/10 px-3 py-1 text-white/70 transition hover:border-cyan-400/60 hover:text-cyan-100 disabled:opacity-60"
                    >
                      Reset password
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDisable(user)}
                      disabled={
                        workingId === user.id || !user.is_active || !isAdmin
                      }
                      className="rounded-full border border-white/10 px-3 py-1 text-white/70 transition hover:border-rose-400/60 hover:text-rose-100 disabled:opacity-60"
                    >
                      Desactivar
                    </button>
                  </div>
                </div>
              ))}
              {!users.length && !loading ? (
                <div className="px-6 py-6 text-sm text-white/60">
                  No hay usuarios registrados.
                </div>
              ) : null}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
