/**
===============================================================================
TARJETA CRC - apps/frontend/config/jest.setup.ts (Jest Setup)
===============================================================================

Responsabilidades:
  - Registrar matchers de Testing Library.
  - Mockear dependencias del runtime de Next.
  - Limpiar mocks entre tests.

Colaboradores:
  - @testing-library/jest-dom
  - Jest
===============================================================================
*/

import "@testing-library/jest-dom";

import { TextDecoder, TextEncoder } from "util";

// Mock de next/navigation para tests de UI.
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock global de fetch para evitar requests reales.
global.fetch = jest.fn();
// TextEncoder/TextDecoder para tests de streaming (SSE).
global.TextEncoder =
  TextEncoder as unknown as typeof globalThis.TextEncoder;
global.TextDecoder =
  TextDecoder as unknown as typeof globalThis.TextDecoder;

// Reset de mocks entre tests para aislar escenarios.
beforeEach(() => {
  jest.clearAllMocks();
});
