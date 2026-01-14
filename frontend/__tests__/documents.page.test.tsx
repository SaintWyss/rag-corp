import { render, screen } from "@testing-library/react";
import DocumentsPage from "../app/documents/page";

jest.mock("../app/lib/api", () => ({
    listDocuments: jest.fn().mockResolvedValue({ documents: [] }),
    getDocument: jest.fn(),
    deleteDocument: jest.fn(),
    ingestText: jest.fn(),
    ingestBatch: jest.fn(),
}));

describe("Documents Page", () => {
    it("renders documents heading and loads list", async () => {
        render(<DocumentsPage />);

        expect(
            await screen.findByText(/Documentos y carga/i)
        ).toBeInTheDocument();
        expect(
            await screen.findByText(/Aun no hay documentos/i)
        ).toBeInTheDocument();
    });
});
