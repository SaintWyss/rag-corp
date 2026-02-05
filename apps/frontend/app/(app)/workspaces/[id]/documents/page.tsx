/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/documents/page.tsx (Page docs workspace)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de documentos dentro del contexto de un workspace.
  - Normalizar parámetros de query relevantes para el screen (ej: documento preferido).
  - Mantener wiring puro (params/searchParams -> props), sin fetch ni side-effects.

Colaboradores:
  - features/documents/components/DocumentsScreen
  - React

Invariantes:
  - La validación del `workspaceId` se realiza en el layout `workspaces/[id]/layout.tsx`.
  - `preferredDocumentId` debe ser string no vacío o undefined (nunca string vacío).
===============================================================================
*/

import { DocumentsScreen } from "@/features/documents/components/DocumentsScreen";

type WorkspaceDocumentsSearchParams = {
  /**
   * Documento preferido a abrir/seleccionar (puede venir como string o array por el parser de Next).
   */
  doc?: string | string[];
};

type PageProps = {
  params: Promise<{
    /**
     * Segmento dinámico validado por el boundary del workspace.
     */
    id: string;
  }>;
  /**
   * Query params del request actual (server component).
   */
  searchParams?: WorkspaceDocumentsSearchParams;
};

/**
 * Normaliza el parámetro `doc` de forma defensiva.
 * - Acepta string o string[] (tomamos el primer valor).
 * - Trim + eliminación de vacío (retorna undefined si es inválido).
 */
function normalizePreferredDocumentId(
  raw?: string | string[],
): string | undefined {
  const candidate = Array.isArray(raw) ? raw[0] : raw;
  if (typeof candidate !== "string") {
    return undefined;
  }
  const trimmed = candidate.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

/**
 * Página de documentos del workspace.
 * - Wiring puro: transforma params/searchParams en props para el screen.
 */
export default async function WorkspaceDocumentsPage({
  params,
  searchParams,
}: PageProps) {
  const { id } = await params;
  const preferredDocumentId = normalizePreferredDocumentId(searchParams?.doc);

  return (
    <DocumentsScreen
      workspaceId={id}
      preferredDocumentId={preferredDocumentId}
    />
  );
}
