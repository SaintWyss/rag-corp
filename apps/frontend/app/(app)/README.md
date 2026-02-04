# apps/frontend/app/(app)

Grupo de rutas principal de la **Aplicación** (portal autenticado).

## 🎯 Propósito

Agrupar todas las pantallas que requieren:

1. **Sesión activa** (autenticación).
2. **Layout de aplicación** (shell/chrome) aplicado por secciones.
3. **Wiring de rutas** (params, redirects, boundaries) sin lógica de producto.

> Regla de arquitectura: `app/` es routing + wiring.  
> La lógica de producto vive en `src/features/*` y lo compartido en `src/shared/*`.

## 🧱 Boundaries del grupo

Este grupo define boundaries globales para UX consistente:

- `error.tsx`: error recuperable del grupo (reset).
- `loading.tsx`: skeleton neutro.
- `not-found.tsx`: 404 del grupo.

## 📍 Rutas y Portales

Este grupo se organiza en portales:

### 🛡️ Portal Admin (`/admin`)

Gestión de plataforma.

- `/admin/users`: ABM de usuarios.
- `/admin/workspaces`: Gestión global de workspaces.

Notas:
- El `AdminShell` se aplica en `app/(app)/admin/layout.tsx`.
- El guard de rol admin se centraliza en ese layout.

### 💼 Portal Workspaces (`/workspaces`)

Uso diario de empleados/usuarios.

- `/workspaces`: Listado de workspaces accesibles.
- `/workspaces/[id]`: Dashboard de un workspace específico.
- `/workspaces/[id]/chat`: Interfaz de chat RAG.
- `/workspaces/[id]/documents`: Gestión de documentos del workspace.

Notas:
- El shell de esta sección (AppShell) debe aplicarse a nivel de layout del portal `/workspaces`
  para evitar duplicación en pages.
- El segmento `workspaces/[id]` actúa como boundary del contexto workspace (validación de `id` + slots).

---
