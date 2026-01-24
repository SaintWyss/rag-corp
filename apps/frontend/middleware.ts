import { sanitizeNextPath } from "@/shared/lib/safeNext";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * Next.js middleware for authentication and route protection.
 * 
 * This middleware:
 * - Protects private routes (/workspaces, /documents, /chat, /admin) by checking for JWT cookie
 * - Redirects unauthenticated users to /login?next=<current-path>
 * - Redirects authenticated users away from /login to their intended destination or /workspaces
 * - Does NOT intercept /api/* or /auth/* (those are rewrites to the backend)
 */
export function middleware(req: NextRequest) {
    const { pathname, searchParams } = req.nextUrl;

    // Check for authentication cookie
    // Try common cookie names (backend configurable)
    const cookieName =
        process.env.JWT_COOKIE_NAME ||
        process.env.NEXT_PUBLIC_JWT_COOKIE_NAME ||
        "rag_access_token"; // fallback to most common name

    const authCookie =
        req.cookies.get(cookieName)?.value ||
        req.cookies.get("access_token")?.value; // secondary fallback

    const isAuthed = Boolean(authCookie);

    // Private routes: require authentication
    const isPrivateRoute =
        pathname.startsWith("/workspaces") ||
        pathname.startsWith("/documents") ||
        pathname.startsWith("/chat") ||
        pathname.startsWith("/admin");

    if (isPrivateRoute && !isAuthed) {
        // Redirect to login with next parameter (includes search params if any)
        const url = req.nextUrl.clone();
        const fullPath = searchParams.toString()
            ? `${pathname}?${searchParams.toString()}`
            : pathname;

        url.pathname = "/login";
        url.search = ""; // Clear existing search params
        url.searchParams.set("next", fullPath);
        return NextResponse.redirect(url);
    }

    // Special case: /login when already authenticated
    if (pathname === "/login" && isAuthed) {
        // Redirect to safe next path or default
        const nextParam = searchParams.get("next");
        const safePath = sanitizeNextPath(nextParam);

        const url = req.nextUrl.clone();
        url.pathname = safePath;
        url.search = ""; // Clear search params
        return NextResponse.redirect(url);
    }

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
