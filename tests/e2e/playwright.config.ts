import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Configuration for RAG Corp E2E Tests
 *
 * @see https://playwright.dev/docs/test-configuration
 */
const useCompose = process.env.E2E_USE_COMPOSE === "1";
const baseURL = process.env.E2E_BASE_URL || "http://localhost:3000";

export default defineConfig({
    testDir: "./tests",
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI
        ? [["github"], ["html", { open: "never" }]]
        : "html",
    outputDir: "test-results",

    /* Shared settings for all projects */
    use: {
        /* Base URL for navigation */
        baseURL,

        /* Collect trace/video on failure */
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
        video: "retain-on-failure",
    },

    /* Configure projects for major browsers */
    projects: process.env.CI
        ? [
              {
                  name: "chromium",
                  use: { ...devices["Desktop Chrome"] },
              },
          ]
        : [
              {
                  name: "chromium",
                  use: { ...devices["Desktop Chrome"] },
              },
              {
                  name: "firefox",
                  use: { ...devices["Desktop Firefox"] },
              },
          ],

    /* Start local dev server before running tests (local dev) */
    webServer: useCompose
        ? undefined
        : [
              {
                  command: "cd ../../apps/backend && uvicorn app.main:app --port 8000",
                  url: "http://localhost:8000/healthz",
                  reuseExistingServer: !process.env.CI,
                  timeout: 60000,
              },
              {
                  command: "cd ../../apps/frontend && pnpm dev",
                  url: baseURL,
                  reuseExistingServer: !process.env.CI,
                  timeout: 60000,
              },
          ],
});
