import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Configuration for RAG Corp E2E Tests
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
    testDir: "./tests",
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? "github" : "html",

    /* Shared settings for all projects */
    use: {
        /* Base URL for navigation */
        baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",

        /* Collect trace on first retry */
        trace: "on-first-retry",

        /* Screenshot on failure */
        screenshot: "only-on-failure",
    },

    /* Configure projects for major browsers */
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
        {
            name: "firefox",
            use: { ...devices["Desktop Firefox"] },
        },
        // Uncomment for WebKit testing
        // {
        //   name: "webkit",
        //   use: { ...devices["Desktop Safari"] },
        // },
    ],

    /* Start local dev server before running tests */
    webServer: [
        {
            command: "cd ../../backend && uvicorn app.main:app --port 8000",
            url: "http://localhost:8000/healthz",
            reuseExistingServer: !process.env.CI,
            timeout: 60000,
        },
        {
            command: "cd ../../frontend && pnpm dev",
            url: "http://localhost:3000",
            reuseExistingServer: !process.env.CI,
            timeout: 60000,
        },
    ],
});
