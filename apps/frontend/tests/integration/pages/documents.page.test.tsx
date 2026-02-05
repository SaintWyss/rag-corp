/**
===============================================================================
TARJETA CRC - apps/frontend/tests/integration/pages/documents.page.test.tsx
===============================================================================
Responsabilidades:
  - Verificar el flujo de documentos en el frontend (render + permisos).
  - Asegurar que el UI refleja estados y roles sin errores.

Colaboradores:
  - app/(app)/workspaces/[id]/documents/page
  - src/features/documents/components/DocumentsScreen.tsx
===============================================================================
*/

import { fireEvent, render, screen } from "@testing-library/react";

import {
  getCurrentUser,
  getWorkspaceDocument,
  listWorkspaceDocuments,
  listWorkspaces,
  reprocessWorkspaceDocument,
  uploadWorkspaceDocument,
} from "@/shared/api/api";
import { getStoredApiKey } from "@/shared/lib/apiKey";

import DocumentsPage from "../../../app/(app)/workspaces/[id]/documents/page";

jest.mock("@/shared/lib/apiKey", () => ({
  getStoredApiKey: jest.fn(),
}));

jest.mock("@/shared/api/api", () => ({
  listWorkspaceDocuments: jest.fn(),
  getWorkspaceDocument: jest.fn(),
  uploadWorkspaceDocument: jest.fn(),
  reprocessWorkspaceDocument: jest.fn(),
  listWorkspaces: jest.fn(),
  getCurrentUser: jest.fn(),
}));

describe("Documents Page", () => {
  beforeEach(() => {
    (getStoredApiKey as jest.Mock).mockReturnValue("");
    (uploadWorkspaceDocument as jest.Mock).mockResolvedValue({});
    (reprocessWorkspaceDocument as jest.Mock).mockResolvedValue({});
    (listWorkspaces as jest.Mock).mockResolvedValue({ workspaces: [] });
  });

  it("renders sources and failed status details", async () => {
    (listWorkspaceDocuments as jest.Mock).mockResolvedValue({
      documents: [
        {
          id: "doc-1",
          title: "Manual PDF",
          source: "https://example.com",
          metadata: {},
          created_at: "2024-01-01T12:00:00Z",
          status: "FAILED",
          file_name: "manual.pdf",
          mime_type: "application/pdf",
          tags: ["legal", "handbook"],
        },
      ],
      next_cursor: null,
    });
    (getWorkspaceDocument as jest.Mock).mockResolvedValue({
      id: "doc-1",
      title: "Manual PDF",
      source: "https://example.com",
      metadata: {},
      created_at: "2024-01-01T12:00:00Z",
      status: "FAILED",
      file_name: "manual.pdf",
      mime_type: "application/pdf",
      error_message: "Parser failed",
      tags: ["legal", "handbook"],
    });
    (getCurrentUser as jest.Mock).mockResolvedValue(null);

    render(
      await DocumentsPage({ params: Promise.resolve({ id: "workspace-1" }) })
    );

    expect(
      await screen.findByRole("heading", { name: "Sources" })
    ).toBeInTheDocument();
    expect(
      await screen.findByTestId("sources-search-input")
    ).toBeInTheDocument();

    const item = await screen.findByTestId("sources-item-doc-1");
    fireEvent.click(item);

    expect(item).toHaveTextContent("FAILED");
    expect(item).toHaveTextContent("legal");
  });

  it("hides admin actions for employee role", async () => {
    (getStoredApiKey as jest.Mock).mockReturnValue("e2e-key");
    (listWorkspaceDocuments as jest.Mock).mockResolvedValue({
      documents: [
        {
          id: "doc-2",
          title: "Specs",
          source: null,
          metadata: {},
          created_at: "2024-01-01T12:00:00Z",
          status: "READY",
          file_name: "specs.pdf",
          mime_type: "application/pdf",
        },
      ],
      next_cursor: null,
    });
    (getWorkspaceDocument as jest.Mock).mockResolvedValue({
      id: "doc-2",
      title: "Specs",
      source: null,
      metadata: {},
      created_at: "2024-01-01T12:00:00Z",
      status: "READY",
      file_name: "specs.pdf",
      mime_type: "application/pdf",
    });
    (getCurrentUser as jest.Mock).mockResolvedValue({
      id: "user-1",
      email: "employee@example.com",
      role: "employee",
      is_active: true,
    });

    render(
      await DocumentsPage({ params: Promise.resolve({ id: "workspace-1" }) })
    );

    const item = await screen.findByTestId("sources-item-doc-2");
    fireEvent.click(item);
    expect(screen.queryByTestId("sources-upload-panel")).toBeNull();
    expect(screen.queryByTestId("sources-reprocess")).toBeNull();
    expect(screen.queryByTestId("sources-delete")).toBeNull();
  });
});
