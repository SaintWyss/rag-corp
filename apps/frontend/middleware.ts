/**
===============================================================================
TARJETA CRC — apps/frontend/middleware.ts (Auth + Role Routing)
===============================================================================

Responsabilidades:
  - Proteger rutas privadas redirigiendo no autenticados a /login.
  - Validar sesión vía /auth/me del backend.
  - Enforcear portal correcto según rol (admin/employee).
  - Sanitizar `next` para evitar open-redirects.
  - Fail-safe: si el backend falla o timeoutea, forzar login.

Colaboradores:
  - NextRequest/NextResponse (middleware runtime)
  - `sanitizeNextPath` (seguridad de redirects)
  - Backend `/auth/me` (validación de sesión)

Patrones aplicados:
  - Front Controller (política de acceso centralizada).
  - Fail-safe redirect (si backend falla, se fuerza login).
  - Guard Clauses (salidas tempranas para legibilidad y seguridad).

Errores y respuestas:
  - Sin cookie en ruta privada: redirect a /login?next=...
  - /auth/me falla o timeoutea: redirect a /login + limpieza de cookies.
  - `next` inválido: se ignora y se envía a home por rol.

Invariantes:
  - Nunca se redirige a URL externa.
  - Si el backend falla, el sistema cierra acceso (fail-safe).
  - Admin y employee no cruzan portales.

Notas:
  - No depende de `RAG_BACKEND_URL`: usa same-origin + rewrites como fuente única.
  - Evitar `NEXT_PUBLIC_*` aquí salvo compat temporal.
  - Timeout recomendado para /auth/me (default 1500ms) para evitar colgar edge.
===============================================================================
*/

import { parseAuthMe, type AuthRole } from "@/shared/api/contracts";
import { apiRoutes } from "@/shared/api/routes";
import { sanitizeNextPath } from "@/shared/lib/safeNext";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

// Rutas “home” por rol (portal correcto).
const ADMIN_HOME = "/admin/users";
const EMPLOYEE_HOME = "/workspaces";

/**
 * Timeout para la validación de sesión.
 * Evita que un backend lento “congele” el middleware.
 */
function parseTimeoutMs(raw: string | undefined, fallbackMs: number): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallbackMs;
  // Clamp defensivo: evita aborts instantáneos o hangs largos.
  const min = 250;
  const max = 5000;
  return Math.min(Math.max(parsed, min), max);
}

const AUTH_ME_TIMEOUT_MS = parseTimeoutMs(process.env.AUTH_ME_TIMEOUT_MS, 1500);
const COOKIE_DOMAIN = process.env.JWT_COOKIE_DOMAIN || undefined;

/**
 * Helper para abortar fetch por timeout.
 * Nota: en edge/runtime, AbortController es soportado; si no lo fuera, el try/catch
 * igual aplica (fail-safe a login).
 */
function withTimeout(ms: number): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => clearTimeout(id) };
}

/**
 * Llama al backend `/auth/me` pasando cookies del request original.
 * - Si no hay cookie header: no hay sesión.
 * - Si response no OK / timeout / parse inválido: consideramos no autenticado.
 *
 * Seguridad:
 * - No logueamos cookies ni headers.
 * - Validamos role + is_active para no confiar ciegamente en payload.
 */
async function fetchCurrentUser(req: NextRequest) {
  const cookieHeader = req.headers.get("cookie");
  if (!cookieHeader) return null;

  // Same-origin: el rewrite es el source of truth del backend.
  const url = new URL(apiRoutes.auth.me, req.nextUrl.origin);
  const { signal, clear } = withTimeout(AUTH_ME_TIMEOUT_MS);

  try {
    const response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        Cookie: cookieHeader,
        Accept: "application/json",
      },
      cache: "no-store",
      signal,
    });

    if (!response.ok) return null;

    // Parse defensivo (si backend cambia o responde error HTML, etc.)
    const raw: unknown = await response.json();
    const user = parseAuthMe(raw);
    if (!user) return null;
    if (user.is_active !== true) return null;
    return user;
  } catch (error) {
    // Observabilidad best-effort. Evitar info sensible.
    console.error("[Middleware] /auth/me failed or timed out:", error);
    return null;
  } finally {
    clear();
  }
}

function getHomeForRole(role: AuthRole): string {
  return role === "admin" ? ADMIN_HOME : EMPLOYEE_HOME;
}

/**
 * Determina si el usuario está intentando entrar a un portal que no corresponde.
 * - Admin no debería navegar /workspaces.
 * - Employee no debería navegar /admin.
 */
function isWrongPortal(pathname: string, role: AuthRole): boolean {
  if (role === "admin") return pathname.startsWith("/workspaces");
  return pathname.startsWith("/admin");
}

/**
 * Borrado de cookie robusto:
 * - Setea cookie vacía con maxAge=0 y path=/ para cubrir cookies comunes.
 */
function deleteCookie(response: NextResponse, name: string) {
  response.cookies.set({ name, value: "", maxAge: 0, path: "/" });
  if (COOKIE_DOMAIN) {
    response.cookies.set({ name, value: "", maxAge: 0, path: "/", domain: COOKIE_DOMAIN });
  }
}

/**
 * Middleware principal:
 * - Aplica solo en matcher (login + rutas privadas).
 * - Usa guard clauses para legibilidad y “fail closed”.
 */
export async function middleware(req: NextRequest) {
  const { pathname, searchParams } = req.nextUrl;

  /**
   * Nombre del cookie JWT:
   * - Preferimos server-only `JWT_COOKIE_NAME`.
   * - Default: `rag_access_token`.
   * Nota: `NEXT_PUBLIC_JWT_COOKIE_NAME` es temporal para compat.
   */
  const cookieName =
    process.env.JWT_COOKIE_NAME ||
    process.env.NEXT_PUBLIC_JWT_COOKIE_NAME || // DEPRECADO: migrar a JWT_COOKIE_NAME
    "rag_access_token";

  /**
   * Detección de cookie:
   * - req.cookies es el parser de Next.
   * - Se consideran alias por compat.
   */
  const authCookie =
    req.cookies.get(cookieName)?.value ||
    req.cookies.get("access_token")?.value ||
    req.cookies.get("rag_access_token")?.value;

  const hasCookie = Boolean(authCookie);

  // Definición de rutas privadas.
  const isPrivateRoute = pathname.startsWith("/workspaces") || pathname.startsWith("/admin");
  const isLoginPage = pathname === "/login";

  // Si no es privada ni login, no hacemos nada.
  if (!isPrivateRoute && !isLoginPage) return NextResponse.next();

  /**
   * Caso 1: Ruta privada sin cookie → redirect a /login.
   * - Preservamos la ruta destino en `next`.
   * - `next` NO se sanitiza aquí porque lo generamos nosotros (desde pathname).
   */
  if (isPrivateRoute && !hasCookie) {
    const url = req.nextUrl.clone();

    const fullPath = searchParams.toString()
      ? `${pathname}?${searchParams.toString()}`
      : pathname;

    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("next", fullPath);

    return NextResponse.redirect(url);
  }

  /**
   * Caso 2: Hay cookie → validamos sesión real con backend.
   * - Defensa: cookie puede estar vencida/invalidada.
   */
  if (hasCookie) {
    const user = await fetchCurrentUser(req);

    /**
     * Sesión inválida:
     * - Redirect a login
     * - Limpia cookies para evitar loops y estados “fantasma”
     */
    if (!user) {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      url.search = "";

      // Si venías de ruta privada, preservamos return-to.
      if (isPrivateRoute) {
        const fullPath = searchParams.toString()
          ? `${pathname}?${searchParams.toString()}`
          : pathname;
        url.searchParams.set("next", fullPath);
      }

      const response = NextResponse.redirect(url);
      deleteCookie(response, cookieName);
      deleteCookie(response, "access_token");
      deleteCookie(response, "rag_access_token");
      return response;
    }

    const role = user.role;

    /**
     * Caso 2a: Estás en /login pero ya autenticado.
     * - Si existe `next`, lo sanitizamos (evita open-redirect).
     * - Si `next` apunta al portal incorrecto, ignoramos y mandamos home correcto.
     */
    if (isLoginPage) {
      const nextParam = searchParams.get("next");

      if (nextParam) {
        const safePath = sanitizeNextPath(nextParam);

        if (!isWrongPortal(safePath, role)) {
          const url = req.nextUrl.clone();
          url.pathname = safePath;
          url.search = "";
          return NextResponse.redirect(url);
        }
      }

      const url = req.nextUrl.clone();
      url.pathname = getHomeForRole(role);
      url.search = "";
      return NextResponse.redirect(url);
    }

    /**
     * Caso 2b: Estás autenticado pero en portal incorrecto → redirect al correcto.
     */
    if (isWrongPortal(pathname, role)) {
      const url = req.nextUrl.clone();
      url.pathname = getHomeForRole(role);
      url.search = "";
      return NextResponse.redirect(url);
    }

    // Caso 2c: Todo OK → continuar.
    return NextResponse.next();
  }

  // Fallback seguro (no debería ocurrir por la lógica anterior).
  return NextResponse.next();
}

/**
 * Matcher:
 * - Restringe dónde corre el middleware (performance + menor riesgo de efectos).
 */
export const config = {
  matcher: ["/login", "/workspaces/:path*", "/admin/:path*"],
};
