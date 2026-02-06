/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/shared/ui.test.tsx (UI shared)
===============================================================================
Responsabilidades:
  - Cubrir componentes simples compartidos (input, fondo, header).
  - Asegurar renderizacion basica sin errores.

Colaboradores:
  - src/shared/ui/components/*
===============================================================================
*/

import { fireEvent, render, screen } from "@testing-library/react";

import { ApiKeyInput } from "@/shared/ui/components/ApiKeyInput";
import { AuroraBackground } from "@/shared/ui/components/AuroraBackground";
import { PageHeader } from "@/shared/ui/components/PageHeader";

describe("shared/ui/components", () => {
  it("ApiKeyInput refleja cambios en el input", () => {
    render(<ApiKeyInput />);
    const input = screen.getByLabelText("API Key") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "abc" } });
    expect(input.value).toBe("abc");
  });

  it("AuroraBackground renderiza hijos", () => {
    render(
      <AuroraBackground data-testid="aurora">
        <span>hola</span>
      </AuroraBackground>
    );
    expect(screen.getByText("hola")).toBeInTheDocument();
    expect(screen.getByTestId("aurora")).toBeInTheDocument();
  });

  it("PageHeader muestra textos clave", () => {
    render(<PageHeader />);
    expect(
      screen.getByText(/Busqueda semantica con respuestas trazables/i)
    ).toBeInTheDocument();
  });
});
