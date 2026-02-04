/**
===============================================================================
TARJETA CRC - apps/frontend/src/app-shell/guards/AdminGuard.tsx (Guard admin)
===============================================================================
Responsabilidades:
  - Verificar sesión y rol admin en server-side.
  - Redirigir a login o portal de workspaces si no cumple.

Colaboradores:
  - next/headers (cookies, headers)
  - next/navigation (redirect)

Notas / Invariantes:
  - No expone datos sensibles en logs.
  - Usa /auth/me (mismo origen) para validar rol.
===============================================================================
*/

import type { ReactNode } from "react";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import { apiRoutes } from "@/shared/api/routes";
import { parseAuthMe, type AuthMe } from "@/shared/api/contracts";

type AdminGuardProps = {
  children: ReactNode;
};

async function fetchCurrentUser(): Promise<AuthMe | null> {
  const cookieHeader = cookies().toString();
  if (!cookieHeader) {
    return null;
  }

  const reqHeaders = headers();
  const host =
    reqHeaders.get("x-forwarded-host") || reqHeaders.get("host");
  if (!host) {
    return null;
  }

  const proto = reqHeaders.get("x-forwarded-proto") || "http";
  const url = `${proto}://${host}${apiRoutes.auth.me}`;

  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: {
        cookie: cookieHeader,
      },
    });

    if (!response.ok) {
      return null;
    }

    const payload = await response.json();
    const user = parseAuthMe(payload);
    if (!user || user.is_active !== true) {
      return null;
    }
    return user;
  } catch {
    return null;
  }
}

/**
 * Guard server-side para el portal admin.
 */
export async function AdminGuard({ children }: AdminGuardProps) {
  const user = await fetchCurrentUser();

  if (!user) {
    redirect("/login?next=/admin/users");
  }

  if (user.role !== "admin") {
    redirect("/workspaces");
  }

  return <>{children}</>;
}
