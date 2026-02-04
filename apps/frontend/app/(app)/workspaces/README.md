# apps/frontend/app/(app)/workspaces

Sección principal para la interacción RAG por workspace (portal de usuarios).

## 🎯 Misión
Proveer el portal `/workspaces` y su contexto `[id]` con wiring limpio, aplicando el shell y los boundaries necesarios sin lógica de producto.

### Qué SÍ hace
- Define el portal `/workspaces` y sus rutas anidadas por workspace.
- Aplica `AppShell` a nivel de layout para todo el portal.
- Centraliza el boundary del segmento `[id]` (validación y 404).
- Refuerza que chat y documentos viven solo bajo `/workspaces/[id]` (sin rutas globales).

### Qué NO hace (y por qué)
- No implementa lógica de negocio. Razón: vive en `src/features/*`. Consecuencia: las pages solo delegan en screens.
- No realiza fetch en layouts o pages. Razón: routing puro. Consecuencia: la data se carga en los screens.
- No duplica el shell en pages. Razón: el layout ya aplica `AppShell`. Consecuencia: evitar UI duplicada.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Portada y guía del portal workspaces. |
| `layout.tsx` | Archivo | Aplica `AppShell` al portal `/workspaces/**`. |
| `page.tsx` | Archivo | Wiring del listado/selector de workspaces. |
| `[id]/layout.tsx` | Archivo | Boundary del workspace (validación de id). |
| `[id]/page.tsx` | Archivo | Home del workspace (wiring). |
| `[id]/chat/page.tsx` | Archivo | Chat RAG scoped por workspace (wiring). |
| `[id]/documents/page.tsx` | Archivo | Documentos del workspace (wiring). |
| `[id]/error.tsx` | Archivo | Error boundary del segmento `[id]`. |
| `[id]/loading.tsx` | Archivo | Loading del segmento `[id]`. |
| `[id]/not-found.tsx` | Archivo | 404 del segmento `[id]`. |

## ⚙️ ¿Cómo funciona por dentro?
- `layout.tsx` envuelve todas las rutas `/workspaces/**` con `AppShell`.
- `workspaces/[id]/layout.tsx` valida el `id` y hace fail-fast con `notFound()`.
- Cada page delega a un screen en `src/features/*` (wiring puro).
- Los boundaries del segmento `[id]` aíslan errores y estados de carga por workspace.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** portal de usuarios (workspaces) con contexto explícito.
- **Recibe órdenes de:** router de Next.js.
- **Llama a:** `shared/ui/shells/AppShell`, `features/workspaces/components/WorkspacesScreen`, `WorkspaceHomeScreen`, `ChatScreen`, `DocumentsScreen`.
- **Reglas de límites:** no lógica de negocio ni fetch; solo routing y composición.

## 👩‍💻 Guía de uso (Snippets)
```tsx
import { WorkspaceHomeScreen } from "@/features/workspaces/components/WorkspaceHomeScreen";

export default function WorkspaceHomePage({ params }: { params: { id: string } }) {
  return <WorkspaceHomeScreen workspaceId={params.id} />;
}
```

## 🧩 Cómo extender sin romper nada
- Si agregás una subruta nueva bajo `[id]`, mantené el wiring puro y pasa `workspaceId` por props.
- No envuelvas pages con `AppShell`; el layout del portal ya lo aplica.
- Usá el boundary `[id]/layout.tsx` para validaciones de id, no en las pages.

## 🆘 Troubleshooting
- **Síntoma:** el portal no muestra `AppShell`.
- **Causa probable:** `layout.tsx` no envuelve correctamente.
- **Dónde mirar:** `workspaces/layout.tsx`.
- **Solución:** envolver `children` con `AppShell`.
- **Síntoma:** 404 en workspace válido.
- **Causa probable:** normalización del `id` falla.
- **Dónde mirar:** `workspaces/[id]/layout.tsx`.
- **Solución:** ajustar validación del `id`.
- **Síntoma:** chat/documents no recibe `workspaceId`.
- **Causa probable:** page no propaga `params.id` al screen.
- **Dónde mirar:** `workspaces/[id]/chat/page.tsx`, `workspaces/[id]/documents/page.tsx`.
- **Solución:** pasar `workspaceId` desde `params`.

## 🔎 Ver también
- `../README.md`
- `../../README.md`
