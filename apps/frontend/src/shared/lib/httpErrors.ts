/**
===============================================================================
TARJETA CRC - apps/frontend/src/shared/lib/httpErrors.ts (HTTP errors)
===============================================================================
Responsabilidades:
  - Convertir status HTTP en mensajes amigables para UI.
  - Centralizar mensajes para evitar duplicación.

Colaboradores:
  - features/rag hooks
  - shared/api/api.ts
===============================================================================
*/

export function statusToUserMessage(status: number): string {
  switch (status) {
    case 401:
      return "API key requerida. Configura tu clave de acceso.";
    case 403:
      return "Sin permisos para esta operación.";
    case 404:
      return "Recurso no encontrado.";
    case 409:
      return "Conflicto de datos. Revisa el estado actual.";
    case 422:
      return "Datos inválidos. Revisa tu consulta.";
    case 429:
      return "Demasiadas solicitudes. Espera unos segundos e intenta de nuevo.";
    case 503:
      return "Servicio no disponible. Intenta de nuevo en unos minutos.";
    case 500:
    default:
      return `Error del servidor (${status}). Intenta de nuevo.`;
  }
}

export function networkErrorMessage(): string {
  return "Error de conexión. Verifica el backend.";
}
