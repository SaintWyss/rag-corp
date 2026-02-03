// =============================================================================
// TARJETA CRC — apps/frontend/jest.config.js (Shim -> config/jest.config.js)
// =============================================================================
// Responsabilidades:
//   - Mantener compatibilidad con herramientas que buscan config en la raiz.
//   - Re-exportar la config real desde /config.
// Colaboradores:
//   - Jest
// =============================================================================

module.exports = require("./config/jest.config.js");
