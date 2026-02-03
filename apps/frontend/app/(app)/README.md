# apps/frontend/app/(app)

Grupo de rutas principal de la **Aplicación**.

## 🎯 Propósito

Agrupar todas las pantallas que requieren:

1. **Autenticación**: El usuario debe tener sesión activa.
2. **Layout de Aplicación**: Sidebar, Header, Breadcrumbs y Contextos de usuario.

## 📍 Rutas y Portales

Este grupo se bifurca en dos grandes portales según el rol del usuario:

### 🛡️ Portal Admin (`/admin`)

Para gestión de la plataforma.

- `/admin/users`: ABM de usuarios.
- `/admin/workspaces`: Gestión global de workspaces.

### 💼 Portal Workspaces (`/workspaces`)

Para uso diario de empleados/usuarios.

- `/workspaces`: Listado de mis workspaces.
- `/workspaces/[id]`: Dashboard de un workspace específico.
- `/workspaces/[id]/chat`: Interfaz de chat RAG.
- `/workspaces/[id]/documents`: Gestión de documentos del workspace.

---

# =============================================================================

# TARJETA CRC - apps/frontend/app/(app) (Main App Group)

# =============================================================================

# Responsabilidades:

# - Proveer el Shell de la aplicación (Sidebar, Header).

# - Inyectar providers globales de sesión y UI.

# - Separar lógicamente la app del login.

# Colaboradores:

# - `src/shared/ui/AppShell` (Componente visual principal)

# - `middleware.ts` (Protección de estas rutas)

# =============================================================================
