/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/security/csp.test.ts
===============================================================================
Responsabilidades:
  - Verificar que se emite Content-Security-Policy con directivas clave.
  - Evitar regresiones en headers de seguridad del frontend.

Colaboradores:
  - apps/frontend/next.config.mjs

Invariantes:
  - No validar valores sensibles ni agregar dependencias externas.
===============================================================================
*/

import fs from "fs";
import path from "path";

describe("CSP headers", () => {
  it("incluye Content-Security-Policy con directivas base", async () => {
    const configPath = path.resolve(__dirname, "../../../next.config.mjs");
    const contents = fs.readFileSync(configPath, "utf8");

    expect(contents).toContain("Content-Security-Policy");
    expect(contents).toContain("default-src 'self'");
    expect(contents).toContain("base-uri 'self'");
    expect(contents).toContain("object-src 'none'");
    expect(contents).toContain("frame-ancestors 'none'");
    expect(contents).toContain("script-src 'self'");
    expect(contents).toContain("style-src 'self'");
    expect(contents).toContain("connect-src 'self'");
  });
});
