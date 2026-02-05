/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/ui/shells/AppShell.tsx (Shell principal)
===============================================================================
Responsabilidades:
  - Proveer el layout base y navegacion de workspaces.
  - Sincronizar el selector de workspaces con la ruta actual.
  - Mostrar feedback cuando hay errores o ausencia de datos.

Colaboradores:
  - shared/ui/components/AuroraBackground
  - shared/api (workspaces)
===============================================================================
*/
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { listWorkspaces, logout, type WorkspaceSummary } from "@/shared/api/api";
import { ApiKeyInput } from "@/shared/ui/components/ApiKeyInput";
import { AuroraBackground } from "@/shared/ui/components/AuroraBackground";

type AppShellProps = {
  children: React.ReactNode;
};

type WorkspaceRoute = {
  workspaceId: string | null;
  section: "documents" | "chat";
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

function parseWorkspaceRoute(pathname: string | null): WorkspaceRoute {
  if (!pathname) {
    return { workspaceId: null, section: "documents" };
  }
  const match = pathname.match(/^\/workspaces\/([^/]+)(?:\/(documents|chat))?/);
  if (!match) {
    return { workspaceId: null, section: "documents" };
  }
  return {
    workspaceId: match[1] ?? null,
    section: (match[2] as WorkspaceRoute["section"]) ?? "documents",
  };
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [workspacesLoading, setWorkspacesLoading] = useState(false);
  const [workspacesError, setWorkspacesError] = useState("");

  const { workspaceId, section } = useMemo(
    () => parseWorkspaceRoute(pathname),
    [pathname]
  );

  const loadWorkspaces = useCallback(async () => {
    setWorkspacesLoading(true);
    setWorkspacesError("");
    try {
      const res = await listWorkspaces();
      setWorkspaces(res.workspaces);
    } catch (err) {
      setWorkspacesError(formatError(err));
    } finally {
      setWorkspacesLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWorkspaces();
  }, [loadWorkspaces]);


  const visibleWorkspaces = useMemo(
    () => workspaces.filter((workspace) => !workspace.archived_at),
    [workspaces]
  );

  const documentsHref = workspaceId
    ? `/workspaces/${workspaceId}/documents`
    : "/workspaces";
  const chatHref = workspaceId
    ? `/workspaces/${workspaceId}/chat`
    : "/workspaces";

  const navLinks = useMemo(
    () => [
      {
        href: chatHref,
        label: "Chat",
        active: Boolean(
          pathname?.startsWith("/workspaces/") && pathname.includes("/chat")
        ),
      },
      {
        href: documentsHref,
        label: "Sources",
        active: Boolean(
          pathname?.startsWith("/workspaces/") && pathname.includes("/documents")
        ),
      },
      {
        href: "/workspaces",
        label: "Workspaces",
        active: pathname === "/workspaces",
      },
    ],
    [chatHref, documentsHref, pathname]
  );

  const handleWorkspaceChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const nextId = event.target.value;
      if (!nextId) {
        return;
      }
      const targetSection = section === "chat" ? "chat" : "documents";
      router.push(`/workspaces/${nextId}/${targetSection}`);
    },
    [router, section]
  );

  return (
    <div className="min-h-screen font-sans text-white">
      <AuroraBackground className="h-auto min-h-screen items-stretch justify-start bg-zinc-950 text-white transition-bg">
        <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 py-8 sm:px-10 z-10">
          <header className="flex flex-col gap-6 rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/60 font-bold shadow-sm">
                RAG Corp
              </div>
              <nav className="flex flex-wrap items-center gap-4 text-sm font-medium text-white/60">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`rounded-full px-3 py-1 transition ${
                      link.active
                        ? "bg-cyan-400 text-slate-950 shadow-md shadow-cyan-400/20 font-semibold"
                        : "hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-3 text-xs uppercase tracking-[0.2em] text-white/40 font-bold">
                  Workspace
                  <select
                    value={workspaceId ?? ""}
                    onChange={handleWorkspaceChange}
                    disabled={workspacesLoading || visibleWorkspaces.length === 0}
                    data-testid="workspace-selector"
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="" disabled className="bg-zinc-900 text-white">
                      {workspacesLoading
                        ? "Cargando..."
                        : visibleWorkspaces.length
                          ? "Selecciona un workspace"
                          : "Sin workspaces"}
                    </option>
                    {visibleWorkspaces.map((workspace) => (
                      <option
                        key={workspace.id}
                        value={workspace.id}
                        className="bg-zinc-900 text-white"
                      >
                        {workspace.name}
                      </option>
                    ))}
                  </select>
                </label>
                {workspacesLoading ? (
                  <span
                    className="text-xs text-white/40"
                    data-testid="workspace-selector-loading"
                  >
                    Cargando...
                  </span>
                ) : null}
                {workspacesError ? (
                  <span
                    className="text-xs text-rose-400"
                    data-testid="workspace-selector-error"
                  >
                    {workspacesError}
                  </span>
                ) : null}
                {!workspacesLoading &&
                !workspacesError &&
                visibleWorkspaces.length === 0 ? (
                  <span
                    className="text-xs text-white/40"
                    data-testid="workspace-selector-empty"
                  >
                    No hay workspaces visibles.
                  </span>
                ) : null}
              </div>
            </div>
            <div className="flex items-center gap-4 w-full sm:max-w-xs justify-end">
              <ApiKeyInput />
              <Link
                href="/auth/logout"
                className="text-xs font-medium text-white/40 hover:text-white transition"
                onClick={(e) => {
                  e.preventDefault();
                  logout()
                    .catch(() => undefined)
                    .finally(() => {
                      window.location.href = "/login";
                    });
                }}
              >
                Logout
              </Link>
            </div>
          </header>

          {children}
        </div>
      </AuroraBackground>
    </div>
  );
}
