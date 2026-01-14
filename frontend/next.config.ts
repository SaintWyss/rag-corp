/**
 * Name: Next.js Configuration (Development Proxy)
 * 
 * Responsibilities:
 *   - Configure rewrites for transparent proxy to backend
 *   - Avoid CORS in development (same origin for /v1/*)
 * 
 * Collaborators:
 *   - Next.js rewrites API
 *   - Backend at http://127.0.0.1:8000
 * 
 * Constraints:
 *   - Defaults to localhost (set NEXT_PUBLIC_API_URL for production)
 * 
 * Notes:
 *   - :path* captures everything after /v1/ (greedy match)
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
        // R: Proxy all /v1/* requests to backend
        source: "/v1/:path*",  // R: Match pattern (greedy)
        destination: `${backendUrl}/v1/:path*`,  // R: Backend URL
      },
    ];
  },
};

export default nextConfig;
