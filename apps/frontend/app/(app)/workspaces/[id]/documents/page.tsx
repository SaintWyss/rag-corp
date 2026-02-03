/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/workspaces/[id]/documents/page.tsx (Page docs workspace)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de documentos con workspace.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/documents/DocumentsScreen
===============================================================================
*/

import { DocumentsScreen } from "@/features/documents/components/DocumentsScreen";

type PageProps = {
  params: {
    id: string;
  };
  searchParams?: {
    doc?: string | string[];
  };
};

export default function WorkspaceDocumentsPage({ params, searchParams }: PageProps) {
  const docParam = Array.isArray(searchParams?.doc)
    ? searchParams?.doc[0]
    : searchParams?.doc;
  const preferredDocumentId = docParam?.trim() ? docParam : undefined;

  return (
    <DocumentsScreen
      workspaceId={params.id}
      preferredDocumentId={preferredDocumentId}
    />
  );
}
