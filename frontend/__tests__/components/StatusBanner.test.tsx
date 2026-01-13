import { render, screen } from "@testing-library/react";
import { StatusBanner } from "../../app/components/StatusBanner";

describe("StatusBanner Component", () => {
    it("renders nothing when message is empty", () => {
        const { container } = render(<StatusBanner message="" />);
        expect(container).toBeEmptyDOMElement();
    });

    it("renders nothing when message is null/undefined", () => {
        // @ts-expect-error - testing edge case
        const { container } = render(<StatusBanner message={null} />);
        expect(container).toBeEmptyDOMElement();
    });

    it("renders the error message", () => {
        const errorMessage = "Ha ocurrido un error al procesar la solicitud.";
        render(<StatusBanner message={errorMessage} />);

        expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it("renders with correct styling classes", () => {
        render(<StatusBanner message="Error message" />);

        const banner = screen.getByText("Error message");
        expect(banner).toHaveClass("rounded-2xl");
        expect(banner).toHaveClass("border");
    });

    it("handles long error messages", () => {
        const longMessage = "Error: " + "x".repeat(500);
        render(<StatusBanner message={longMessage} />);

        expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it("handles messages with special characters", () => {
        const specialMessage = "Error: <script>alert('xss')</script>";
        render(<StatusBanner message={specialMessage} />);

        // Should render as text, not execute
        expect(screen.getByText(specialMessage)).toBeInTheDocument();
    });

    it("handles messages with newlines", () => {
        const multilineMessage = "Line 1\nLine 2\nLine 3";
        render(<StatusBanner message={multilineMessage} />);

        // Use regex matcher due to whitespace normalization
        expect(screen.getByText(/Line 1/)).toBeInTheDocument();
        expect(screen.getByText(/Line 2/)).toBeInTheDocument();
    });

    it("renders different error types", () => {
        const errorTypes = [
            "Error de red: No se pudo conectar al servidor",
            "Error 401: No autorizado",
            "Error 500: Error interno del servidor",
            "Error de validación: El campo es requerido",
        ];

        errorTypes.forEach((error) => {
            const { unmount } = render(<StatusBanner message={error} />);
            expect(screen.getByText(error)).toBeInTheDocument();
            unmount();
        });
    });

    it("updates when message prop changes", () => {
        const { rerender } = render(<StatusBanner message="First error" />);
        expect(screen.getByText("First error")).toBeInTheDocument();

        rerender(<StatusBanner message="Second error" />);
        expect(screen.getByText("Second error")).toBeInTheDocument();
        expect(screen.queryByText("First error")).not.toBeInTheDocument();
    });

    it("disappears when message becomes empty", () => {
        const { rerender, container } = render(<StatusBanner message="Error" />);
        expect(screen.getByText("Error")).toBeInTheDocument();

        rerender(<StatusBanner message="" />);
        expect(container).toBeEmptyDOMElement();
    });
});
