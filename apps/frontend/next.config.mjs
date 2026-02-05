/**
===============================================================================
TARJETA CRC — apps/frontend/next.config.mjs (Proxy/Rewrites Next.js)
===============================================================================

Responsabilidades:
  - Definir rewrites para proxy transparente hacia el backend.
  - Evitar CORS en desarrollo usando mismo origen para /api y /auth.
  - Centralizar el "contrato" de rutas reservadas del frontend: /api, /auth, /v1.

Colaboradores:
  - Next.js (rewrites API)
  - Backend API (HTTP)

Patrones aplicados:
  - Reverse proxy por rewrites (BFF liviano desde el edge del frontend).

Errores y respuestas:
  - Si el backend no responde, el cliente recibe el error HTTP resultante.
  - Si falta `RAG_BACKEND_URL`, se usa el fallback según entorno.

Invariantes:
  - Solo se proxyean prefijos reservados (/api, /auth, /v1).
  - El browser siempre habla con el mismo origen (no expone URL externa).

Notas:
  - Server-only: usar `RAG_BACKEND_URL` para no depender de variables públicas.
  - `/api` y `/auth` quedan reservadas por estos rewrites.
  - `/v1` es un shim opcional de compatibilidad (si no lo necesitás, se elimina).
===============================================================================
*/

/** @type {import('next').NextConfig} */
const nextConfig = {
  // R: Produce standalone output for the production Docker image.
  output: "standalone",
  /**
   * Security headers (baseline).
   * - CSP se construye en middleware (nonce por request).
   * - X-Frame-Options para evitar embedding.
   * - Ajustes defensivos comunes.
   */
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  /**
   * Rewrites:
   * - Permiten que el browser hable "con el mismo origen" (frontend) y Next.js
   *   reenvía al backend internamente.
   * - Resultado: evita CORS, simplifica cookies httpOnly (SameSite/Lax) y reduce
   *   configuración en el backend.
   *
   * Importante:
   * - Este mapping define qué prefijos quedan "reservados" en el frontend.
   * - El backend debe ser quien implemente auth + política real; aquí solo
   *   enrutamos (proxy).
   */
  async rewrites() {
    // Fallback razonable para entorno local y docker-compose.
    // - production: nombre de servicio en red docker.
    // - dev: localhost.
    const fallback =
      process.env.NODE_ENV === "production"
        ? "http://rag-api:8000"
        : "http://127.0.0.1:8000";

    /**
     * `RAG_BACKEND_URL`:
     * - Variable server-only (preferida).
     * - Evita usar `NEXT_PUBLIC_*` (que sugiere exposición al cliente).
     */
    const backendUrl = (process.env.RAG_BACKEND_URL || fallback).replace(/\/$/, "");

    /**
     * Orden de rewrites:
     * - Se evalúan en orden.
     * - Primero rutas más específicas, luego más generales.
     */
    return [
      /**
       * Auth:
       * - Mantiene el prefijo /auth en el mismo origen (frontend)
       * - Forward al backend /auth/*
       * - Útil para cookies httpOnly en mismo site/origin.
       */
      {
        source: "/auth/:path*",
        destination: `${backendUrl}/auth/:path*`,
      },

      /**
       * Admin API:
       * - En el frontend usamos /api/admin/* pero en backend puede ser /admin/*
       * - Esto evita “mezclar” en el cliente los prefijos del backend.
       */
      {
        source: "/api/admin/:path*",
        destination: `${backendUrl}/admin/:path*`,
      },

      /**
       * API pública versionada:
       * - Frontend llama /api/* y se mapea a /v1/*
       * - Ventaja: el cliente nunca conoce /v1 (o conoce, pero no depende).
       */
      {
        source: "/api/:path*",
        destination: `${backendUrl}/v1/:path*`,
      },

      /**
       * Shim opcional:
       * - Si alguien consume directamente /v1 desde el frontend (por compat),
       *   se forwardea igual.
       * - Si querés mínima superficie, eliminá este rewrite.
       */
      {
        source: "/v1/:path*",
        destination: `${backendUrl}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
