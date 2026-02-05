/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/security/csp.test.ts
===============================================================================
Responsabilidades:
  - Verificar que se emite Content-Security-Policy con directivas clave.
  - Evitar regresiones en headers de seguridad del frontend.

Colaboradores:
  - shared/security/csp.ts

Invariantes:
  - No validar valores sensibles ni agregar dependencias externas.
===============================================================================
*/

import { buildCspHeader } from "@/shared/security/csp";

describe("CSP headers", () => {
  it("incluye Content-Security-Policy con directivas base", async () => {
    const csp = buildCspHeader({ nonce: "test-nonce", isDev: false });

    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("script-src 'self' 'unsafe-inline'");
    expect(csp).toContain("style-src 'self' 'unsafe-inline'");
    expect(csp).toContain("connect-src 'self'");
    expect(csp).toContain("unsafe-inline");
  });
});
