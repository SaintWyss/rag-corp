/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/contracts/auth.ts (Auth contracts)
===============================================================================
Responsabilidades:
  - Definir el shape mínimo esperado de /auth/me.
  - Proveer un parser defensivo para validar payloads en runtime.

Colaboradores:
  - middleware.ts
  - app-shell/guards/AdminGuard.tsx
===============================================================================
*/

export type AuthRole = "admin" | "employee";

export type AuthMe = {
  id: string;
  email: string;
  role: AuthRole;
  is_active: boolean;
  created_at?: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isAuthRole(value: unknown): value is AuthRole {
  return value === "admin" || value === "employee";
}

/**
 * Parser defensivo de /auth/me.
 * - Retorna null si el payload no cumple el contrato mínimo.
 */
export function parseAuthMe(raw: unknown): AuthMe | null {
  if (!isRecord(raw)) return null;

  const id = raw.id;
  const email = raw.email;
  const role = raw.role;
  const isActive = raw.is_active;
  const createdAt = raw.created_at;

  if (typeof id !== "string") return null;
  if (typeof email !== "string") return null;
  if (!isAuthRole(role)) return null;
  if (typeof isActive !== "boolean") return null;

  if (createdAt !== undefined && createdAt !== null && typeof createdAt !== "string") {
    return null;
  }

  return {
    id,
    email,
    role,
    is_active: isActive,
    created_at: createdAt ?? null,
  };
}
