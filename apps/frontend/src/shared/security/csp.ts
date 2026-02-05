/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/security/csp.ts (CSP builder)
===============================================================================
Responsabilidades:
  - Construir el header Content-Security-Policy con nonce y directivas base.
  - Evitar unsafe-inline y permitir ajustes por entorno (dev vs prod).

Colaboradores:
  - middleware.ts (inyecta el header en responses)

Invariantes:
  - No incluir secretos ni valores sensibles.
  - Mantener CSP explícito por directiva (sin defaults implícitos).
  - Conservar 'unsafe-inline' por compatibilidad con inline scripts/estilos de Next.
===============================================================================
*/

type CspOptions = {
  nonce: string;
  isDev: boolean;
};

export function buildCspHeader({ nonce, isDev }: CspOptions): string {
  const directives = [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `script-src 'self' 'nonce-${nonce}' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'nonce-${nonce}' 'unsafe-inline'`,
    `connect-src 'self'${isDev ? " ws: wss:" : ""}`,
  ];

  return directives.join("; ");
}
