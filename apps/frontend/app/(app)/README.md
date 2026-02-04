# apps/frontend/app/(app)

Grupo de rutas principal del portal autenticado (routing + wiring).

## 🎯 Misión
Asegurar un entrypoint consistente para el portal autenticado y concentrar el wiring de rutas y boundaries comunes sin mezclar lógica de producto.

### Qué SÍ hace
- Agrupa rutas que requieren sesión activa bajo un mismo route group.
- Provee boundaries globales del grupo (`error.tsx`, `loading.tsx`, `not-found.tsx`).
- Define el entrypoint del portal y el redirect seguro en `page.tsx`.
- Organiza los portales `/admin` y `/workspaces` con layouts propios.

### Qué NO hace (y por qué)
- No contiene lógica de producto. Razón: el negocio vive en `src/features/*`. Consecuencia: las pages solo delegan en screens.
- No aplica guards de rol aquí. Razón: los guards se centralizan por portal. Consecuencia: admin/workspaces definen sus reglas en sus layouts.
- No monta un shell global. Razón: cada portal usa su propio chrome. Consecuencia: `AppShell`/`AdminShell` se aplican en layouts específicos.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Portada y mapa del route group. |
| `layout.tsx` | Archivo | Layout neutro del grupo (sin guards ni shell). |
| `page.tsx` | Archivo | Entry point con redirect seguro al portal. |
| `error.tsx` | Archivo | Error boundary del grupo (recuperable). |
| `loading.tsx` | Archivo | Skeleton/placeholder neutro del grupo. |
| `not-found.tsx` | Archivo | 404 del grupo. |
| `admin/` | Carpeta | Portal administrativo. |
| `workspaces/` | Carpeta | Portal principal de usuarios. |

## ⚙️ ¿Cómo funciona por dentro?
- `page.tsx` normaliza `next` con `sanitizeNextPath` y redirige a un destino seguro (default: `/workspaces`).
- `layout.tsx` provee un `<main>` neutro sin side-effects ni guards.
- Cada portal define su propio layout y su shell (`AdminShell` o `AppShell`).
- Los boundaries del grupo manejan errores/loads comunes para rutas hijas.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** route group del portal autenticado (wiring + boundaries).
- **Recibe órdenes de:** Next.js router y middleware de auth.
- **Llama a:** `shared/lib/safeNext`, layouts de portal y screens en `src/features/*`.
- **Reglas de límites:** no traer lógica de producto ni fetch; solo routing y composición.

## 👩‍💻 Guía de uso (Snippets)
```tsx
import { redirect } from "next/navigation";
import { sanitizeNextPath } from "@/shared/lib/safeNext";

export default function AppEntryPage({ searchParams }) {
  const rawNext = Array.isArray(searchParams?.next)
    ? searchParams?.next[0]
    : searchParams?.next;
  const target = sanitizeNextPath(rawNext) || "/workspaces";
  redirect(target);
}
```

## 🧩 Cómo extender sin romper nada
- Si agregás un portal nuevo, creá una carpeta con su propio `layout.tsx` y README.
- Mantené las pages del grupo como wiring puro (sin fetch ni lógica de producto).
- Centralizá guards por portal para evitar duplicación.

## 🆘 Troubleshooting
- **Síntoma:** redirect loops al entrar al portal.
- **Causa probable:** `next` inválido o middleware mal configurado.
- **Dónde mirar:** `page.tsx` y `shared/lib/safeNext`.
- **Solución:** validar el `next` y usar fallback seguro.
- **Síntoma:** falta el shell en un portal.
- **Causa probable:** layout del portal no aplica `AppShell`/`AdminShell`.
- **Dónde mirar:** `admin/layout.tsx` o `workspaces/layout.tsx`.
- **Solución:** aplicar el shell en el layout del portal.
- **Síntoma:** 404 en un workspace válido.
- **Causa probable:** validación del `id` falla en el boundary.
- **Dónde mirar:** `workspaces/[id]/layout.tsx`.
- **Solución:** ajustar la normalización del `id` o la ruta.

## 🔎 Ver también
- `./admin/README.md`
- `./workspaces/README.md`
- `../../README.md`
