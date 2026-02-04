import { render, screen } from "@testing-library/react";
import DocumentsPage from "../../../app/(app)/workspaces/[id]/documents/page";
import { getStoredApiKey } from "@/shared/lib/apiKey";
import {
  getCurrentUser,
  getWorkspaceDocument,
  listWorkspaceDocuments,
  listWorkspaces,
  reprocessWorkspaceDocument,
  uploadWorkspaceDocument,
} from "@/shared/api/api";

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

    render(<DocumentsPage params={{ id: "workspace-1" }} />);

    expect(
      await screen.findByRole("heading", { name: "Sources" })
    ).toBeInTheDocument();
    expect(await screen.findByTestId("sources-search-input")).toBeInTheDocument();
    expect(await screen.findByTestId("source-status-chip")).toHaveTextContent(
      "FAILED"
    );
    expect(await screen.findByTestId("source-detail-error")).toHaveTextContent(
      "Parser failed"
    );
    expect(await screen.findByTestId("source-detail-tags")).toHaveTextContent(
      "legal"
    );
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

    render(<DocumentsPage params={{ id: "workspace-1" }} />);

    await screen.findByTestId("source-detail");
    expect(screen.queryByTestId("sources-upload-panel")).toBeNull();
    expect(screen.queryByTestId("source-reprocess-button")).toBeNull();
  });
});
