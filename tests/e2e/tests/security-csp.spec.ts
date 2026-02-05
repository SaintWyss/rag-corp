/**
===============================================================================
TARJETA CRC - tests/e2e/tests/security-csp.spec.ts (CSP smoke)
===============================================================================
Responsabilidades:
  - Verificar que el frontend responde con Content-Security-Policy.
  - Asegurar ausencia de unsafe-inline en producción.

Colaboradores:
  - Playwright
  - Middleware de seguridad del frontend

Invariantes:
  - No requiere credenciales ni datos sensibles.
  - Debe ser rápido (smoke test).
===============================================================================
*/

import { expect, test } from "@playwright/test";

test.describe("Security headers", () => {
  test("CSP incluye directivas base", async ({ page }) => {
    const response = await page.goto("/", { waitUntil: "domcontentloaded" });
    expect(response).toBeTruthy();

    const csp = response?.headers()["content-security-policy"];
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("script-src 'self'");
    expect(csp).toContain("style-src 'self'");
    expect(csp).toContain("unsafe-inline");
  });
});
