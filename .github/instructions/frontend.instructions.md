---
applyTo: "apps/web/**"
---

- Next.js + TypeScript: separar UI (componentes) de lógica de fetch.
- No duplicar DTOs: usar `packages/contracts` para tipos/cliente.
- Manejo de errores: mostrar mensajes específicos (4xx vs 5xx) cuando sea posible.
- Mantener componentes pequeños y claros. Evitar lógica de negocio en `page.tsx`.
- Comentarios CRC en componentes/módulos principales (JSDoc).
