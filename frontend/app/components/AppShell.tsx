"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ApiKeyInput } from "./ApiKeyInput";

type AppShellProps = {
  children: React.ReactNode;
};

const links = [
  { href: "/", label: "Ask" },
  { href: "/chat", label: "Chat" },
  { href: "/documents", label: "Documents" },
];

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.15),_transparent_55%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,_rgba(14,116,144,0.2),_transparent_45%)]" />
        <div className="relative mx-auto flex max-w-6xl flex-col gap-10 px-6 py-12 sm:px-10">
          <header className="flex flex-col gap-6 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-white/60">
                RAG Corp · v1
              </div>
              <nav className="flex flex-wrap items-center gap-4 text-sm font-medium text-white/70">
                {links.map((link) => {
                  const active =
                    pathname === link.href ||
                    (link.href !== "/" && pathname?.startsWith(link.href));
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`rounded-full px-3 py-1 transition ${
                        active
                          ? "bg-cyan-400/20 text-cyan-100"
                          : "bg-white/0 text-white/60 hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      {link.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="w-full sm:max-w-xs">
              <ApiKeyInput />
            </div>
          </header>

          {children}
        </div>
      </div>
    </div>
  );
}
