/**
===============================================================================
TARJETA CRC - apps/frontend/tests/unit/pages/page.test.tsx
===============================================================================
Responsabilidades:
  - Validar redirect inicial de la Home.

Colaboradores:
  - app/page
  - next/navigation (mock)

Invariantes:
  - Sin llamadas de red.
===============================================================================
*/

import { redirect } from "next/navigation";

import Home from "../../../app/page";

jest.mock("next/navigation", () => ({
  redirect: jest.fn(),
}));

describe("Home Page", () => {
  it("redirects to login", () => {
    Home();
    expect(redirect).toHaveBeenCalledWith("/login");
  });
});
