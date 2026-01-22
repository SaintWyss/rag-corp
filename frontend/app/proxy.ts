import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Protect /app/*: require auth cookie set by backend (/auth/login)
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow public and next internals
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon.ico")
  ) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/app")) {
    // Cookie name is controlled by backend settings, but defaults to ACCESS_TOKEN_COOKIE.
    // We'll accept either the default or a custom name if you configured it.
    const hasAnyAuthCookie =
      req.cookies.get("access_token")?.value || req.cookies.get("rag_access_token")?.value;

    if (!hasAnyAuthCookie) {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("next", pathname);
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*"],
};
