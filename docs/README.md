# Portal de documentación
Guía principal para navegar el backend y sus contratos sin duplicar detalle técnico.

## Empezar por intención
- Backend (mapa por capas) → `index/backend.md`
- API y contratos → `index/api.md`
- Operación y runbooks → `index/ops.md`
- Datos y migraciones → `index/data.md`
- Seguridad y control de acceso → `index/security.md`
- Calidad y testing → `index/quality.md`

## Mapas rápidos del backend (fuente de verdad)
- Arquitectura general y capas → `../apps/backend/app/README.md`
- Casos de uso (Application) → `../apps/backend/app/application/README.md`
- HTTP (routers + schemas) → `../apps/backend/app/interfaces/api/http/README.md`
- Infraestructura (DB, repos, colas, servicios) → `../apps/backend/app/infrastructure/README.md`
- Worker y jobs → `../apps/backend/app/worker/README.md`
- Prompts versionados → `../apps/backend/app/prompts/README.md`

## Referencias transversales
- Configuración y variables → `reference/config.md`
- Errores RFC7807 y códigos → `reference/errors.md`
- Control de acceso (JWT/API keys/RBAC) → `reference/access-control.md`
- Límites del sistema → `reference/limits.md`
