/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/api/contracts/problem.ts (RFC7807)
===============================================================================
Responsabilidades:
  - Definir el contrato de Problem Details (RFC7807) usado por el backend.
  - Normalizar payloads desconocidos a un shape seguro.

Colaboradores:
  - shared/api/api.ts

Notas / Invariantes:
  - Campos opcionales para tolerar variantes de backend.
===============================================================================
*/

export type ApiProblem = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: Record<string, string[]>;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Normaliza un payload a ApiProblem (best-effort).
 */
export function normalizeProblem(
  payload: unknown,
  status?: number
): ApiProblem | undefined {
  if (!isObject(payload)) {
    return status ? { status, title: "Error" } : undefined;
  }

  const problem: ApiProblem = {
    type: typeof payload.type === "string" ? payload.type : undefined,
    title: typeof payload.title === "string" ? payload.title : undefined,
    status: typeof payload.status === "number" ? payload.status : status,
    detail: typeof payload.detail === "string" ? payload.detail : undefined,
    instance: typeof payload.instance === "string" ? payload.instance : undefined,
    errors: isObject(payload.errors) ? (payload.errors as Record<string, string[]>) : undefined,
  };

  return problem;
}
