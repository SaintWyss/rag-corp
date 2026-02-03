/**
===============================================================================
TARJETA CRC — apps/frontend/config/jest.setup.ts (Jest Setup)
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

// Mock next/navigation
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

// Mock fetch globally
global.fetch = jest.fn();

// Reset mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
});
