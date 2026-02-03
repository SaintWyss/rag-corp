# apps/frontend/app/(app)/admin

Sección dedicada a la **Administración del Sistema**.

## 📍 Rutas

| Ruta                | Archivo               | Funcionalidad                                                                          |
| :------------------ | :-------------------- | :------------------------------------------------------------------------------------- |
| `/admin/users`      | `users/page.tsx`      | **Gestión de Usuarios**. Crear, editar, desactivar usuarios y asignar roles.           |
| `/admin/workspaces` | `workspaces/page.tsx` | **Gestión de Workspaces**. Visión global de todos los espacios de trabajo del sistema. |

## 🔒 Seguridad

- Estas rutas están protegidas por `middleware.ts`.
- Solo usuarios con `role: "admin"` pueden acceder.

---

# =============================================================================

# TARJETA CRC - apps/frontend/app/(app)/admin (Admin Portal)

# =============================================================================

# Responsabilidades:

# - Exponer pantallas CRUD para entidades del sistema.

# - Servir como punto de entrada para tareas de mantenimiento.

# Colaboradores:

# - `src/features/admin` (Lógica de administración)

# - `src/shared/ui/AdminShell` (Layout específico de admin si aplica)

# =============================================================================
