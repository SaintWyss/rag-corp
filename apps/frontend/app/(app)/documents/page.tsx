/**
===============================================================================
TARJETA CRC - apps/frontend/app/(app)/documents/page.tsx (Page documents)
===============================================================================
Responsabilidades:
  - Enrutar a la screen de documentos.
  - Mantener el wiring sin logica de producto.

Colaboradores:
  - features/documents/DocumentsScreen
  - shared/ui/AppShell
===============================================================================
*/

import { DocumentsScreen } from "@/features/documents/components/DocumentsScreen";
import { AppShell } from "@/shared/ui/AppShell";

type PageProps = {
  searchParams?: {
    doc?: string | string[];
  };
};

export default function DocumentsPage({ searchParams }: PageProps) {
  const docParam = Array.isArray(searchParams?.doc)
    ? searchParams?.doc[0]
    : searchParams?.doc;
  const preferredDocumentId = docParam?.trim() ? docParam : undefined;

  return (
    <AppShell>
      <DocumentsScreen preferredDocumentId={preferredDocumentId} />
    </AppShell>
  );
}
