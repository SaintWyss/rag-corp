# apps/frontend/app/(app)/workspaces

Sección principal para la **Interacción con Documentos (RAG)**.

## 📍 Rutas

### Nivel Superior

| Ruta          | Archivo    | Descripción                                                           |
| :------------ | :--------- | :-------------------------------------------------------------------- |
| `/workspaces` | `page.tsx` | **Selector de Workspace**. Muestra los espacios asignados al usuario. |

### Detalle de Workspace (`[id]`)

Rutas anidadas dinámicas bajo `/workspaces/[id]`. El `[id]` corresponde al UUID del workspace.

| Ruta                         | Archivo                   | Descripción                                                       |
| :--------------------------- | :------------------------ | :---------------------------------------------------------------- |
| `/workspaces/[id]`           | `[id]/page.tsx`           | **Dashboard**. Resumen del workspace, métricas o "quick actions". |
| `/workspaces/[id]/chat`      | `[id]/chat/page.tsx`      | **Chat RAG**. Interfaz conversacional con los documentos.         |
| `/workspaces/[id]/documents` | `[id]/documents/page.tsx` | **Gestión Documental**. Subida (ingestion) y listado de archivos. |

---

# =============================================================================

# TARJETA CRC - apps/frontend/app/(app)/workspaces (User Portal)

# =============================================================================

# Responsabilidades:

# - Enrutar flujos de trabajo del usuario final (Chat, Documentos).

# - Manejar parámetros dinámicos (`[id]`) para contextos de workspace.

# Colaboradores:

# - `src/features/workspaces` (Lógica de workspaces)

# - `src/features/chat` (Lógica de chat)

# - `src/features/documents` (Lógica de documentos)

# =============================================================================
