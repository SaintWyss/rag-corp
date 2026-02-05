/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/components/AnswerCard.test.tsx
===============================================================================
Responsabilidades:
  - Validar rendering y accesibilidad de AnswerCard.
  - Cubrir casos de respuesta vacía y contenido largo.

Colaboradores:
  - shared/ui/components/AnswerCard

Invariantes:
  - Sin llamadas de red.
===============================================================================
*/

import { render, screen } from "@testing-library/react";

import { AnswerCard } from "@/shared/ui/components/AnswerCard";

describe("AnswerCard Component", () => {
    it("renders nothing when answer is empty", () => {
        const { container } = render(<AnswerCard answer="" />);
        expect(container).toBeEmptyDOMElement();
    });

    it("renders nothing when answer is null/undefined", () => {
        // @ts-expect-error - testing edge case
        const { container } = render(<AnswerCard answer={null} />);
        expect(container).toBeEmptyDOMElement();
    });

    it("renders the answer text", () => {
        const testAnswer = "Esta es la respuesta del sistema RAG.";
        render(<AnswerCard answer={testAnswer} />);

        expect(screen.getByText(testAnswer)).toBeInTheDocument();
    });

    it("renders section with correct heading", () => {
        render(<AnswerCard answer="Test answer" />);

        expect(screen.getByRole("region")).toBeInTheDocument();
        expect(screen.getByText("Respuesta")).toBeInTheDocument();
    });

    it("renders Gemini badge", () => {
        render(<AnswerCard answer="Test answer" />);

        expect(screen.getByText("Gemini")).toBeInTheDocument();
    });

    it("has proper accessibility attributes", () => {
        render(<AnswerCard answer="Test answer" />);

        const section = screen.getByRole("region");
        expect(section).toHaveAttribute("aria-labelledby", "answer-heading");
        expect(section).toHaveAttribute("aria-live", "polite");
    });

    it("renders long answers without truncation", () => {
        const longAnswer = "A".repeat(1000);
        render(<AnswerCard answer={longAnswer} />);

        expect(screen.getByText(longAnswer)).toBeInTheDocument();
    });

    it("preserves whitespace in answers", () => {
        const answerWithSpaces = "Line 1\nLine 2\nLine 3";
        render(<AnswerCard answer={answerWithSpaces} />);

        // Use regex matcher due to whitespace normalization
        expect(screen.getByText(/Line 1/)).toBeInTheDocument();
        expect(screen.getByText(/Line 2/)).toBeInTheDocument();
    });
});
