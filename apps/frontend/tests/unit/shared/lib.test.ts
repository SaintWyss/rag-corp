/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/shared/lib.test.ts (Cobertura shared/lib)
===============================================================================
Responsabilidades:
  - Validar utilidades compartidas (formatters, errores HTTP, redirect seguro).
  - Aumentar cobertura en helpers puros.

Colaboradores:
  - src/shared/lib/*
  - src/shared/config/env
===============================================================================
*/

import { cn } from "@/shared/lib/cn";
import { formatDate, formatError, truncateId } from "@/shared/lib/formatters";
import { networkErrorMessage, statusToUserMessage } from "@/shared/lib/httpErrors";
import { SAFE_DEFAULT_AFTER_LOGIN, sanitizeNextPath } from "@/shared/lib/safeNext";

describe("shared/lib helpers", () => {
  it("cn combina clases y deduplica", () => {
    const result = cn("foo", { bar: true, baz: false }, "foo");
    expect(result).toContain("foo");
    expect(result).toContain("bar");
  });

  it("formatError devuelve mensajes esperados", () => {
    expect(formatError(null)).toBe("Error inesperado.");
    expect(formatError("boom")).toBe("boom");
    expect(formatError({ message: "fail" })).toBe("fail");
  });

  it("formatDate maneja vacios e invalidos", () => {
    expect(formatDate()).toBe("Sin fecha");
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatDate("2024-01-01T00:00:00.000Z")).not.toBe("Sin fecha");
  });

  it("truncateId recorta cuando supera el limite", () => {
    expect(truncateId("abcd", 8)).toBe("abcd");
    expect(truncateId("abcdefghij", 4)).toBe("abcd...");
  });

  it("statusToUserMessage traduce codigos HTTP", () => {
    expect(statusToUserMessage(401)).toMatch(/API key/);
    expect(statusToUserMessage(403)).toMatch(/Sin permisos/);
    expect(statusToUserMessage(409)).toMatch(/Conflicto/);
    expect(statusToUserMessage(422)).toMatch(/Datos inválidos/);
    expect(statusToUserMessage(429)).toMatch(/Demasiadas solicitudes/);
    expect(statusToUserMessage(503)).toMatch(/Servicio no disponible/);
    expect(statusToUserMessage(404)).toMatch(/no encontrado/i);
    expect(statusToUserMessage(500)).toMatch(/Error del servidor/);
  });

  it("networkErrorMessage es estable", () => {
    expect(networkErrorMessage()).toBe("Error de conexión. Verifica el backend.");
  });

  it("sanitizeNextPath bloquea redirects peligrosos", () => {
    expect(sanitizeNextPath(null)).toBe(SAFE_DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("http://example.com")).toBe(SAFE_DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("//example.com")).toBe(SAFE_DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("\\\\evil")).toBe(SAFE_DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("/bad\npath")).toBe(SAFE_DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("/workspaces/1")).toBe("/workspaces/1");
  });
});

describe("shared/config/env", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("usa NEXT_PUBLIC_API_TIMEOUT_MS si esta presente", async () => {
    process.env.NEXT_PUBLIC_API_TIMEOUT_MS = "45000";
    const { env } = await import("@/shared/config/env");
    expect(env.apiTimeoutMs).toBe(45000);
  });

  it("usa fallback si el valor no es numerico", async () => {
    process.env.NEXT_PUBLIC_API_TIMEOUT_MS = "nope";
    const { env } = await import("@/shared/config/env");
    expect(env.apiTimeoutMs).toBe(30_000);
  });
});
