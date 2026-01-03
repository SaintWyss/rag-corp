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
};

module.exports = createJestConfig(customJestConfig);
