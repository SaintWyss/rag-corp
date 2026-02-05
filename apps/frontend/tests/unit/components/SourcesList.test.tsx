/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/components/SourcesList.test.tsx
===============================================================================
Responsabilidades:
  - Validar render de SourcesList con 0/1/N fuentes.
  - Verificar headings y artículos.

Colaboradores:
  - shared/ui/components/SourcesList

Invariantes:
  - Sin llamadas de red.
===============================================================================
*/

import { render, screen } from "@testing-library/react";

import { SourcesList } from "@/shared/ui/components/SourcesList";

describe("SourcesList Component", () => {
    it("renders nothing when sources array is empty", () => {
        const { container } = render(<SourcesList sources={[]} />);
        expect(container).toBeEmptyDOMElement();
    });

    it("renders a single source", () => {
        const sources = ["documento-1.pdf"];
        render(<SourcesList sources={sources} />);

        expect(screen.getByText("documento-1.pdf")).toBeInTheDocument();
        expect(screen.getByText("Fuentes")).toBeInTheDocument();
    });

    it("renders multiple sources", () => {
        const sources = ["doc1.pdf", "doc2.md", "doc3.txt"];
        render(<SourcesList sources={sources} />);

        sources.forEach((source) => {
            expect(screen.getByText(source)).toBeInTheDocument();
        });
    });

    it("renders section with correct heading", () => {
        render(<SourcesList sources={["test.pdf"]} />);

        expect(screen.getByText("Fuentes")).toBeInTheDocument();
    });

    it("renders each source as an article", () => {
        const sources = ["source1", "source2"];
        render(<SourcesList sources={sources} />);

        const articles = screen.getAllByRole("article");
        expect(articles).toHaveLength(2);
    });

    it("handles sources with special characters", () => {
        const sources = ["file with spaces.pdf", "archivo-español.doc", "file_underscore.txt"];
        render(<SourcesList sources={sources} />);

        sources.forEach((source) => {
            expect(screen.getByText(source)).toBeInTheDocument();
        });
    });

    it("handles long source names", () => {
        const longSource = "a".repeat(200) + ".pdf";
        render(<SourcesList sources={[longSource]} />);

        expect(screen.getByText(longSource)).toBeInTheDocument();
    });

    it("generates unique keys for sources", () => {
        // Same content but different positions should render correctly
        const sources = ["same.pdf", "different.pdf", "same.pdf"];
        render(<SourcesList sources={sources} />);

        const articles = screen.getAllByRole("article");
        expect(articles).toHaveLength(3);
    });

    it("renders container section", () => {
        render(<SourcesList sources={["test.pdf"]} />);

        // Section without explicit role, query by class or element
        const section = document.querySelector("section");
        expect(section).toBeInTheDocument();
    });
});
