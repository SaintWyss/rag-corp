# apps/frontend/app/(app)/admin

Sección dedicada a la **Administración del Sistema**.

## 🎯 Propósito

- Centralizar pantallas administrativas (gestión de usuarios y workspaces).
- Mantener `app/` como **routing + wiring**: las pages delegan a `src/features/*`.

## 📍 Rutas

| Ruta                | Archivo               | Funcionalidad                                                    |
| :------------------ | :-------------------- | :--------------------------------------------------------------- |
| `/admin/users`      | `users/page.tsx`      | Gestión de usuarios (crear/editar/desactivar/asignar roles).     |
| `/admin/workspaces` | `workspaces/page.tsx` | Gestión global de workspaces (visión completa de la plataforma). |

## 🧱 Boundary del portal admin

- `layout.tsx` aplica el `AdminShell` para toda la sección.
- El guard de rol admin debe centralizarse en `app/(app)/admin/layout.tsx` (server-side cuando sea posible).

## 🔒 Seguridad

- El middleware puede aplicar un guard general de sesión, pero el **guard de rol admin**
  debe estar explícito y centralizado en el layout del portal admin para evitar duplicación.
- Objetivo: que ninguna page admin implemente checks por su cuenta.

---
