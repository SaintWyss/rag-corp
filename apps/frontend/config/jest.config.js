// =============================================================================
// TARJETA CRC — apps/frontend/config/jest.config.js (Jest + Next.js)
// =============================================================================
// Responsabilidades:
//   - Configurar Jest para Next.js (App Router) en el monorepo.
//   - Definir mapeos de paths y umbrales de coverage.
// Colaboradores:
//   - next/jest
//   - Testing Library
// =============================================================================

const path = require("path");
// eslint-disable-next-line @typescript-eslint/no-require-imports -- Jest config runs in CJS.
const nextJest = require("next/jest");

const rootDir = path.resolve(__dirname, "..");

const createJestConfig = nextJest({
  dir: rootDir,
});

/** @type {import('jest').Config} */
const customJestConfig = {
  rootDir,
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  testEnvironment: "jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "^@contracts/(.*)$": "<rootDir>/../shared/contracts/$1",
  },
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/.next/"],
  collectCoverageFrom: ["app/**/*.{ts,tsx}", "!app/**/*.d.ts", "!app/layout.tsx"],
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
