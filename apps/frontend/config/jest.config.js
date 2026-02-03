// =============================================================================
// TARJETA CRC - apps/frontend/config/jest.config.js (Jest + Next.js)
// =============================================================================
// Responsabilidades:
//   - Configurar Jest para Next.js (App Router) en el monorepo.
//   - Centralizar mapeos de paths y reglas de cobertura.
// Colaboradores:
//   - next/jest
//   - Testing Library
// =============================================================================

const path = require("path");
// eslint-disable-next-line @typescript-eslint/no-require-imports -- Jest corre en CJS.
const nextJest = require("next/jest");

const rootDir = path.resolve(__dirname, "..");

const createJestConfig = nextJest({
  dir: rootDir,
});

/** @type {import('jest').Config} */
const customJestConfig = {
  rootDir,
  setupFilesAfterEnv: ["<rootDir>/config/jest.setup.ts"],
  testEnvironment: "jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "^@contracts/(.*)$": "<rootDir>/../shared/contracts/$1",
  },
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/.next/"],
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}",
    "app/**/*.{ts,tsx}",
    "!**/*.d.ts",
    "!**/__tests__/**",
    "!**/*.test.{ts,tsx}",
    "!**/*.spec.{ts,tsx}",
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
};

module.exports = createJestConfig(customJestConfig);
