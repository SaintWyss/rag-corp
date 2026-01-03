import { render, screen } from "@testing-library/react";
import Home from "../app/page";

// Mock the useRagAsk hook
jest.mock("../app/hooks/useRagAsk", () => ({
    useRagAsk: () => ({
        query: "",
        answer: "",
        sources: [],
        loading: false,
        error: "",
        setQuery: jest.fn(),
        submit: jest.fn(),
        reset: jest.fn(),
    }),
}));

describe("Home Page", () => {
    it("renders the page header", () => {
        render(<Home />);
        expect(screen.getByText(/RAG Corp/i)).toBeInTheDocument();
    });

    it("renders the query form", () => {
        render(<Home />);
        // The placeholder contains "Ejemplo" based on actual rendered output
        expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("renders the submit button", () => {
        render(<Home />);
        expect(
            screen.getByRole("button", { name: /preguntar/i })
        ).toBeInTheDocument();
    });
});
