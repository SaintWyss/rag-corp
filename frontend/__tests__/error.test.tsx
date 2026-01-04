import { fireEvent, render, screen } from "@testing-library/react";

let ErrorComponent: typeof import("../app/error").default;

describe("Error Boundary", () => {
    const mockReset = jest.fn();
    const testError = new Error("Test error message");

    beforeAll(async () => {
        // Must import Error component dynamically to avoid useEffect issues in test setup
        ErrorComponent = (await import("../app/error")).default;
    });

    beforeEach(() => {
        mockReset.mockClear();
        // Suppress console.error from the Error component
        jest.spyOn(console, "error").mockImplementation(() => { });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it("renders error message", () => {
        render(<ErrorComponent error={testError} reset={mockReset} />);
        expect(screen.getByText(/algo salió mal/i)).toBeInTheDocument();
        expect(screen.getByText("Test error message")).toBeInTheDocument();
    });

    it("renders retry button", () => {
        render(<ErrorComponent error={testError} reset={mockReset} />);
        expect(
            screen.getByRole("button", { name: /reintentar/i })
        ).toBeInTheDocument();
    });

    it("calls reset when retry button is clicked", () => {
        render(<ErrorComponent error={testError} reset={mockReset} />);
        const retryButton = screen.getByRole("button", { name: /reintentar/i });
        fireEvent.click(retryButton);
        expect(mockReset).toHaveBeenCalledTimes(1);
    });

    it("displays error digest when provided", () => {
        const errorWithDigest = Object.assign(new Error("Error"), {
            digest: "abc123",
        });
        render(<ErrorComponent error={errorWithDigest} reset={mockReset} />);
        expect(screen.getByText(/ID: abc123/)).toBeInTheDocument();
    });
});
