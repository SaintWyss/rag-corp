/**
 * Name: Next.js Configuration (Development Proxy)
 * 
 * Responsibilities:
 *   - Configure rewrites for transparent proxy to backend
 *   - Avoid CORS in development (same origin for /api/*)
 * 
 * Collaborators:
 *   - Next.js rewrites API
 *   - Backend at http://127.0.0.1:8000
 * 
 * Constraints:
 *   - Defaults to localhost (set NEXT_PUBLIC_API_URL for production)
 * 
 * Notes:
 *   - :path* captures everything after /api/ (greedy match)
 *   - 127.0.0.1 preferred over localhost (avoids IPv6 lookup)
 * 
 * Production:
 *   - Set NEXT_PUBLIC_API_URL to your backend base URL
 *   - Or deploy frontend/backend on same domain
 */
import type { NextConfig } from "next";

const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // R: Configure URL rewrites for development proxy
  async rewrites() {
    return [
      {
        // R: Proxy auth routes directly to backend
        source: "/auth/:path*",  // R: Match pattern (greedy)
        destination: `${backendUrl}/auth/:path*`,  // R: Backend URL
      },
      {
        // R: Proxy clean /api/* requests to backend /v1/*
        source: "/api/:path*",  // R: Match pattern (greedy)
        destination: `${backendUrl}/v1/:path*`,  // R: Backend URL
      },
      {
        // R: Backwards compatibility for any legacy /v1/* usage
        source: "/v1/:path*",  // R: Match pattern (greedy)
        destination: `${backendUrl}/v1/:path*`,  // R: Backend URL
      },
    ];
  },
};

export default nextConfig;
