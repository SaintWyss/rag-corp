import { sanitizeNextPath } from "@/shared/lib/safeNext";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

type UserRole = "admin" | "employee";

interface AuthMeResponse {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string | null;
}

const ADMIN_HOME = "/admin/users";
const EMPLOYEE_HOME = "/workspaces";

async function fetchCurrentUser(req: NextRequest): Promise<AuthMeResponse | null> {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://rag-api:8000";
    const baseUrl = backendUrl.replace(/\/$/, "");
    const url = new URL(`${baseUrl}/auth/me`);

    const cookieHeader = req.headers.get("cookie");
    if (!cookieHeader) return null;

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        Cookie: cookieHeader,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) return null;

    const user: AuthMeResponse = await response.json();
    return user;
  } catch (error) {
    console.error("[Middleware] Failed to fetch /auth/me:", error);
    return null;
  }
}

function getHomeForRole(role: UserRole): string {
  return role === "admin" ? ADMIN_HOME : EMPLOYEE_HOME;
}

function isWrongPortal(pathname: string, role: UserRole): boolean {
  if (role === "admin") return pathname.startsWith("/workspaces");
  return pathname.startsWith("/admin");
}

/**
 * Name: Auth and Portal Middleware
 *
 * Responsibilities:
 * - Guard private routes by redirecting unauthenticated users to /login
 * - Validate session cookies by calling the backend /auth/me endpoint
 * - Enforce role-based portal routing between admin and employee areas
 * - Preserve and sanitize ?next= redirects to prevent open redirects
 * - Clear auth cookies when backend validation fails
 *
 * Collaborators:
 * - NextRequest/NextResponse for request inspection and redirects
 * - sanitizeNextPath for safe redirect handling
 * - fetch to call backend authentication endpoint
 * - Environment variables for API base URL and cookie name
 *
 * Notes/Constraints:
 * - Runs only on matcher paths (login/admin/workspaces)
 * - Uses cache: "no-store" to avoid stale auth results
 * - Backend must accept cookie auth on /auth/me
 * - Errors are swallowed to favor safe redirects over 500s
 * - Redirect targets are always internal paths after sanitization
 */
export async function middleware(req: NextRequest) {
  const { pathname, searchParams } = req.nextUrl;

  const cookieName =
    process.env.JWT_COOKIE_NAME ||
    process.env.NEXT_PUBLIC_JWT_COOKIE_NAME ||
    "rag_access_token";

  const authCookie =
    req.cookies.get(cookieName)?.value ||
    req.cookies.get("access_token")?.value ||
    req.cookies.get("rag_access_token")?.value;

  const hasCookie = Boolean(authCookie);

  const isPrivateRoute =
    pathname.startsWith("/workspaces") || pathname.startsWith("/admin");

  const isLoginPage = pathname === "/login";

  if (!isPrivateRoute && !isLoginPage) {
    return NextResponse.next();
  }

  // CASE 1: Private route without cookie => /login?next=
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

  // CASE 2: Has cookie => validate via /auth/me
  if (hasCookie) {
    const user = await fetchCurrentUser(req);

    if (!user) {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      url.search = "";

      if (isPrivateRoute) {
        const fullPath = searchParams.toString()
          ? `${pathname}?${searchParams.toString()}`
          : pathname;
        url.searchParams.set("next", fullPath);
      }

      const response = NextResponse.redirect(url);
      response.cookies.delete(cookieName);
      response.cookies.delete("access_token");
      response.cookies.delete("rag_access_token");
      return response;
    }

    const role = user.role;

    // CASE 2a: /login while authenticated
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

    // CASE 2b: wrong portal
    if (isWrongPortal(pathname, role)) {
      const url = req.nextUrl.clone();
      url.pathname = getHomeForRole(role);
      url.search = "";
      return NextResponse.redirect(url);
    }

    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/login", "/workspaces/:path*", "/admin/:path*"],
};
