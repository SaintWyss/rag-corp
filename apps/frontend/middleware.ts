import { sanitizeNextPath } from "@/shared/lib/safeNext";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * ADR-008: Role-based middleware for Admin Console vs Employee Portal.
 *
 * This middleware:
 * - Protects private routes by checking JWT cookie + /auth/me
 * - Redirects unauthenticated users to /login?next=<current-path>
 * - Redirects authenticated users based on role:
 *   - Admin: if accessing /workspaces/* → redirect to /admin/users
 *   - Employee: if accessing /admin/* → redirect to /workspaces
 * - Redirects authenticated users away from /login to role-appropriate destination
 * - Does NOT intercept /api/* or /auth/* (those are rewrites to the backend)
 */

// Role constants matching backend UserRole enum
type UserRole = "admin" | "employee";

interface AuthMeResponse {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string | null;
}

// Default destinations by role
const ADMIN_HOME = "/admin/users";
const EMPLOYEE_HOME = "/workspaces";

/**
 * Fetch /auth/me to get current user info.
 * Returns null if not authenticated or request fails.
 */
async function fetchCurrentUser(
  req: NextRequest
): Promise<AuthMeResponse | null> {
  try {
    // Build absolute URL for /auth/me (middleware runs server-side)
    const url = new URL("/auth/me", req.nextUrl.origin);

    // Forward cookies from the original request
    const cookieHeader = req.headers.get("cookie");
    if (!cookieHeader) {
      return null;
    }

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: {
        Cookie: cookieHeader,
        Accept: "application/json",
      },
      // No cache to ensure fresh auth state
      cache: "no-store",
    });

    if (!response.ok) {
      // 401/403 means not authenticated or token expired
      return null;
    }

    const user: AuthMeResponse = await response.json();
    return user;
  } catch (error) {
    // Network error, backend down, etc. - treat as not authenticated
    console.error("[Middleware] Failed to fetch /auth/me:", error);
    return null;
  }
}

/**
 * Get role-appropriate home path.
 */
function getHomeForRole(role: UserRole): string {
  return role === "admin" ? ADMIN_HOME : EMPLOYEE_HOME;
}

/**
 * Check if user is trying to access a route they shouldn't.
 */
function isWrongPortal(pathname: string, role: UserRole): boolean {
  if (role === "admin") {
    // Admin should NOT be at /workspaces (employee portal)
    return pathname.startsWith("/workspaces");
  } else {
    // Employee should NOT be at /admin (admin console)
    return pathname.startsWith("/admin");
  }
}

export async function middleware(req: NextRequest) {
  const { pathname, searchParams } = req.nextUrl;

  // Check for authentication cookie (presence only - validation via /auth/me)
  const cookieName =
    process.env.JWT_COOKIE_NAME ||
    process.env.NEXT_PUBLIC_JWT_COOKIE_NAME ||
    "rag_access_token";

  const authCookie =
    req.cookies.get(cookieName)?.value ||
    req.cookies.get("access_token")?.value;

  const hasCookie = Boolean(authCookie);

  // Private routes: require authentication
  const isPrivateRoute =
    pathname.startsWith("/workspaces") ||
    pathname.startsWith("/documents") ||
    pathname.startsWith("/chat") ||
    pathname.startsWith("/admin");

  // Login page - special handling for authenticated users
  const isLoginPage = pathname === "/login";

  // =========================================================================
  // CASE 1: Private route without cookie → redirect to login
  // =========================================================================
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

  // =========================================================================
  // CASE 2: Has cookie → validate with /auth/me and apply role-based logic
  // =========================================================================
  if (hasCookie && (isPrivateRoute || isLoginPage)) {
    const user = await fetchCurrentUser(req);

    // Cookie invalid or expired → redirect to login
    if (!user) {
      // Clear the invalid cookie and redirect to login
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
      // Optionally delete the invalid cookie
      response.cookies.delete(cookieName);
      response.cookies.delete("access_token");
      return response;
    }

    const role = user.role as UserRole;

    // -----------------------------------------------------------------------
    // CASE 2a: Login page while authenticated → redirect to role home
    // -----------------------------------------------------------------------
    if (isLoginPage) {
      const nextParam = searchParams.get("next");

      // If next param exists and is valid for user's role, use it
      if (nextParam) {
        const safePath = sanitizeNextPath(nextParam);
        // Check if the safe path is appropriate for the role
        if (!isWrongPortal(safePath, role)) {
          const url = req.nextUrl.clone();
          url.pathname = safePath;
          url.search = "";
          return NextResponse.redirect(url);
        }
      }

      // Otherwise redirect to role-appropriate home
      const url = req.nextUrl.clone();
      url.pathname = getHomeForRole(role);
      url.search = "";
      return NextResponse.redirect(url);
    }

    // -----------------------------------------------------------------------
    // CASE 2b: Wrong portal for role → redirect to correct portal
    // -----------------------------------------------------------------------
    if (isWrongPortal(pathname, role)) {
      const url = req.nextUrl.clone();
      url.pathname = getHomeForRole(role);
      url.search = "";
      return NextResponse.redirect(url);
    }

    // User is authenticated and on correct portal - proceed
    return NextResponse.next();
  }

  // =========================================================================
  // CASE 3: No cookie, not private route, not login → pass through
  // =========================================================================
  return NextResponse.next();
}

// Only run middleware on specific routes
// This prevents unnecessary checks on static assets, API routes, etc.
export const config = {
  matcher: [
    "/login",
    "/workspaces/:path*",
    "/documents/:path*",
    "/chat/:path*",
    "/admin/:path*",
  ],
};
