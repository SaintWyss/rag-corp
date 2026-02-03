# apps/frontend/app/(app)/workspaces

Sección principal para la **interacción RAG por workspace**.

## 🎯 Propósito

- Servir como portal de navegación del usuario hacia sus workspaces.
- Mantener el **wiring** (routing + params + redirects) sin lógica de producto.
- Delegar UI y casos de uso a `src/features/*`.

> Regla: el shell/chrome (`AppShell`) debe aplicarse por sección a nivel de layout del portal
> (para evitar duplicación en pages y sub-rutas).

## 📍 Rutas

### Nivel Superior

| Ruta          | Archivo    | Descripción                                        |
| :------------ | :--------- | :------------------------------------------------- |
| `/workspaces` | `page.tsx` | Selector de workspaces accesibles para el usuario. |

### Contexto de Workspace (`[id]`)

Rutas anidadas dinámicas bajo `/workspaces/[id]`. El `[id]` corresponde al identificador del workspace.

| Ruta                         | Archivo                   | Descripción                                         |
| :--------------------------- | :------------------------ | :-------------------------------------------------- |
| `/workspaces/[id]`           | `[id]/page.tsx`           | Home del workspace (dashboard / quick actions).     |
| `/workspaces/[id]/chat`      | `[id]/chat/page.tsx`      | Chat RAG dentro del contexto del workspace.         |
| `/workspaces/[id]/documents` | `[id]/documents/page.tsx` | Gestión documental (ingestión, listado, selección). |

## 🧱 Boundaries del segmento `[id]`

El segmento `workspaces/[id]` actúa como boundary:

- `layout.tsx`: valida `id` (fail-fast) y expone slots de wiring (ej. header/breadcrumbs).
- `error.tsx`: error recuperable del segmento (reset).
- `loading.tsx`: skeleton neutro reutilizable.
- `not-found.tsx`: 404 específico del workspace.

---