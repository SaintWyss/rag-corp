import { render, screen } from "@testing-library/react";
import DocumentsPage from "../app/documents/page";
import { getStoredApiKey } from "../app/lib/apiKey";
import {
    getCurrentUser,
    getDocument,
    listDocuments,
    reprocessDocument,
    uploadDocument,
} from "../app/lib/api";

jest.mock("../app/lib/apiKey", () => ({
    getStoredApiKey: jest.fn(),
}));

jest.mock("../app/lib/api", () => ({
    listDocuments: jest.fn(),
    getDocument: jest.fn(),
    uploadDocument: jest.fn(),
    reprocessDocument: jest.fn(),
    getCurrentUser: jest.fn(),
}));

describe("Documents Page", () => {
    beforeEach(() => {
        (getStoredApiKey as jest.Mock).mockReturnValue("");
        (uploadDocument as jest.Mock).mockResolvedValue({});
        (reprocessDocument as jest.Mock).mockResolvedValue({});
    });

    it("renders sources and failed status details", async () => {
        (listDocuments as jest.Mock).mockResolvedValue({
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
                },
            ],
        });
        (getDocument as jest.Mock).mockResolvedValue({
            id: "doc-1",
            title: "Manual PDF",
            source: "https://example.com",
            metadata: {},
            created_at: "2024-01-01T12:00:00Z",
            status: "FAILED",
            file_name: "manual.pdf",
            mime_type: "application/pdf",
            error_message: "Parser failed",
        });
        (getCurrentUser as jest.Mock).mockResolvedValue(null);

        render(<DocumentsPage />);

        expect(
            await screen.findByRole("heading", { name: "Sources" })
        ).toBeInTheDocument();
        expect(await screen.findByTestId("source-status-chip")).toHaveTextContent(
            "FAILED"
        );
        expect(await screen.findByTestId("source-detail-error")).toHaveTextContent(
            "Parser failed"
        );
    });

    it("hides admin actions for employee role", async () => {
        (getStoredApiKey as jest.Mock).mockReturnValue("e2e-key");
        (listDocuments as jest.Mock).mockResolvedValue({
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
        });
        (getDocument as jest.Mock).mockResolvedValue({
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

        render(<DocumentsPage />);

        await screen.findByTestId("source-detail");
        expect(screen.queryByTestId("sources-upload-panel")).toBeNull();
        expect(screen.queryByTestId("source-reprocess-button")).toBeNull();
    });
});
