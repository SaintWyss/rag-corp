/**
===============================================================================
TARJETA CRC - apps/frontend/src/test/fixtures/httpErrors.ts (HTTP error fixtures)
===============================================================================
Responsabilidades:
  - Centralizar códigos de error usados en tests.
===============================================================================
*/

export const HTTP_ERROR_FIXTURES = {
  unauthorized: {
    status: 401,
    message: "API key requerida. Configura tu clave de acceso.",
  },
  rateLimit: {
    status: 429,
    message: "Demasiadas solicitudes. Espera unos segundos e intenta de nuevo.",
  },
  serviceUnavailable: {
    status: 503,
    message: "Servicio no disponible. Intenta de nuevo en unos minutos.",
  },
};
