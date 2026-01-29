import { fireEvent, render, screen } from "@testing-library/react";
import { QueryForm } from "../../src/shared/ui/QueryForm";

describe("QueryForm Component", () => {
    const defaultProps = {
        query: "",
        onQueryChange: jest.fn(),
        onSubmit: jest.fn(),
        loading: false,
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("renders the form with all elements", () => {
        render(<QueryForm {...defaultProps} />);

        expect(screen.getByRole("search")).toBeInTheDocument();
        expect(screen.getByRole("textbox")).toBeInTheDocument();
        expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("displays the query value in textarea", () => {
        render(<QueryForm {...defaultProps} query="test query" />);

        const textarea = screen.getByRole("textbox");
        expect(textarea).toHaveValue("test query");
    });

    it("calls onQueryChange when typing", () => {
        const onQueryChange = jest.fn();
        render(<QueryForm {...defaultProps} onQueryChange={onQueryChange} />);

        const textarea = screen.getByRole("textbox");
        fireEvent.change(textarea, { target: { value: "new query" } });

        expect(onQueryChange).toHaveBeenCalledWith("new query");
    });

    it("calls onSubmit when form is submitted", () => {
        const onSubmit = jest.fn((e) => e.preventDefault());
        render(<QueryForm {...defaultProps} onSubmit={onSubmit} />);

        const form = screen.getByRole("search");
        fireEvent.submit(form);

        expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    it("disables textarea and button when loading", () => {
        render(<QueryForm {...defaultProps} loading={true} />);

        const textarea = screen.getByRole("textbox");
        const button = screen.getByRole("button");

        expect(textarea).toBeDisabled();
        expect(button).toBeDisabled();
    });

    it("shows 'Buscando...' text when loading", () => {
        render(<QueryForm {...defaultProps} loading={true} />);

        expect(screen.getByRole("button", { name: /buscando/i })).toBeInTheDocument();
    });

    it("shows 'Preguntar' text when not loading", () => {
        render(<QueryForm {...defaultProps} loading={false} />);

        expect(screen.getByText("Preguntar")).toBeInTheDocument();
    });

    it("has proper accessibility attributes", () => {
        render(<QueryForm {...defaultProps} />);

        const form = screen.getByRole("search");
        expect(form).toHaveAttribute("aria-label", "Formulario de consulta RAG");

        const textarea = screen.getByRole("textbox");
        expect(textarea).toHaveAttribute("aria-required", "true");
    });

    it("marks textarea as busy when loading", () => {
        render(<QueryForm {...defaultProps} loading={true} />);

        const textarea = screen.getByRole("textbox");
        expect(textarea).toHaveAttribute("aria-busy", "true");
    });

    it("renders placeholder text", () => {
        render(<QueryForm {...defaultProps} />);

        const textarea = screen.getByRole("textbox");
        expect(textarea).toHaveAttribute(
            "placeholder",
            "Ejemplo: Que dice el manual sobre vacaciones?"
        );
    });

    it("button click submits the form", () => {
        const onSubmit = jest.fn((e) => e.preventDefault());
        render(<QueryForm {...defaultProps} onSubmit={onSubmit} />);

        const button = screen.getByRole("button");
        fireEvent.click(button);

        expect(onSubmit).toHaveBeenCalledTimes(1);
    });
});
