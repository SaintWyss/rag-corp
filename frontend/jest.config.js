// eslint-disable-next-line @typescript-eslint/no-require-imports -- Jest config runs in CJS.
const nextJest = require("next/jest");

const createJestConfig = nextJest({
    // Provide the path to your Next.js app
    dir: "./",
});

/** @type {import('jest').Config} */
const customJestConfig = {
    setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
    testEnvironment: "jsdom",
    moduleNameMapper: {
        "^@/(.*)$": "<rootDir>/$1",
        "^@contracts/(.*)$": "<rootDir>/../shared/contracts/$1",
    },
    testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/.next/"],
    collectCoverageFrom: [
        "app/**/*.{ts,tsx}",
        "!app/**/*.d.ts",
        "!app/layout.tsx",
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
