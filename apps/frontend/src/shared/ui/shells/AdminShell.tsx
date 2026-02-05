/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/ui/shells/AdminShell.tsx (Shell admin)
===============================================================================
Responsabilidades:
  - Proveer el layout de administracion y su navegacion principal.
  - Mantener branding y accesos del portal admin.

Colaboradores:
  - shared/ui/components/AuroraBackground
  - next/navigation
===============================================================================
*/
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo } from "react";

import { logout } from "@/shared/api/api";
import { AuroraBackground } from "@/shared/ui/components/AuroraBackground";

type AdminShellProps = {
  children: React.ReactNode;
};

type AdminNavItem = {
  href: string;
  label: string;
  active: boolean;
};

export function AdminShell({ children }: AdminShellProps) {
  const pathname = usePathname();

  const navLinks: AdminNavItem[] = useMemo(
    () => [
      {
        href: "/admin/users",
        label: "Users",
        active: pathname === "/admin/users",
      },
      {
        href: "/admin/workspaces",
        label: "Workspaces",
        active: pathname === "/admin/workspaces",
      },
    ],
    [pathname]
  );

  return (
    <div className="min-h-screen font-sans text-white">
      <AuroraBackground className="h-auto min-h-screen items-stretch justify-start bg-zinc-950 text-white transition-bg">
        <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 py-8 sm:px-10 z-10">
          <header className="flex flex-col gap-6 rounded-3xl border border-white/10 bg-white/5 p-6 shadow-sm backdrop-blur-md sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-3 rounded-full border border-rose-500/20 bg-rose-500/10 px-4 py-2 text-xs uppercase tracking-[0.2em] text-rose-200 font-bold shadow-sm">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-400"></span>
                </span>
                Admin Console
              </div>

              <nav className="flex flex-wrap items-center gap-4 text-sm font-medium text-white/60">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`rounded-full px-3 py-1 transition ${
                      link.active
                        ? "bg-rose-400 text-slate-950 shadow-md shadow-rose-400/20 font-semibold"
                        : "hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>

              <div className="flex flex-wrap items-center gap-3 text-xs text-white/40">
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                  Gestiona usuarios, workspaces y configuración del sistema
                </span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Link
                href="/auth/logout"
                className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-white/60 transition hover:border-rose-400/60 hover:text-rose-100"
                onClick={(e) => {
                  e.preventDefault();
                  logout()
                    .catch(() => undefined)
                    .finally(() => {
                      window.location.href = "/login";
                    });
                }}
              >
                Cerrar sesión
              </Link>
            </div>
          </header>

          {children}
        </div>
      </AuroraBackground>
    </div>
  );
}
