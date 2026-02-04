# apps/frontend/app/(app)/admin

Sección dedicada a la administración del sistema (portal admin).

## 🎯 Misión
Centralizar rutas administrativas y aplicar un shell/guard único para toda la sección sin mezclar lógica de producto en el routing.

### Qué SÍ hace
- Agrupa las rutas de administración bajo `/admin`.
- Aplica `AdminShell` en el layout del portal.
- Provee un punto único para el guard de rol admin.

### Qué NO hace (y por qué)
- No implementa lógica de negocio. Razón: la UI y el estado viven en `src/features/*`. Consecuencia: las pages solo delegan en screens.
- No realiza fetch en el layout. Razón: el layout es wiring. Consecuencia: los datos se resuelven en los screens.
- No dispersa validaciones de rol en cada page. Razón: guard centralizado. Consecuencia: el control se hace en `layout.tsx`.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Portada y guía del portal admin. |
| `layout.tsx` | Archivo | Aplica `AdminShell` y expone el guard admin. |
| `users/page.tsx` | Archivo | Wiring hacia `AdminUsersScreen`. |
| `workspaces/page.tsx` | Archivo | Wiring hacia `AdminWorkspacesScreen`. |

## ⚙️ ¿Cómo funciona por dentro?
- `layout.tsx` envuelve todo el portal con `AdminShell` y un `AdminGuard` centralizado.
- Cada page es delgada: transforma la ruta en el screen correspondiente.
- El guard actualmente es pass-through; es el lugar recomendado para validar rol admin server-side.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** portal administrativo del frontend.
- **Recibe órdenes de:** router de Next.js.
- **Llama a:** `shared/ui/AdminShell`, `features/auth/components/AdminUsersScreen`, `features/workspaces/components/AdminWorkspacesScreen`.
- **Reglas de límites:** routing puro; sin fetch ni lógica de negocio en pages/layouts.

## 👩‍💻 Guía de uso (Snippets)
```tsx
import { AdminUsersScreen } from "@/features/auth/components/AdminUsersScreen";

export default function AdminUsersPage() {
  return <AdminUsersScreen />;
}
```

## 🧩 Cómo extender sin romper nada
- Si agregás una nueva página admin, creá un `page.tsx` que delegue al screen de `src/features/*`.
- Mantén el guard de admin dentro de `layout.tsx` para evitar duplicación.
- No importes infraestructura ni clientes API en el routing.

## 🆘 Troubleshooting
- **Síntoma:** usuarios no admin acceden a `/admin`.
- **Causa probable:** guard no implementado o bypass.
- **Dónde mirar:** `layout.tsx` (`AdminGuard`).
- **Solución:** implementar validación server-side y redirigir.
- **Síntoma:** falta el chrome admin.
- **Causa probable:** `AdminShell` no aplicado en layout.
- **Dónde mirar:** `layout.tsx`.
- **Solución:** envolver `children` con `AdminShell`.
- **Síntoma:** 404 en ruta admin válida.
- **Causa probable:** page faltante o path mal ubicado.
- **Dónde mirar:** `users/page.tsx`, `workspaces/page.tsx`.
- **Solución:** asegurar la ruta bajo `app/(app)/admin/`.

## 🔎 Ver también
- `../README.md`
- `../../README.md`
