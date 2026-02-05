/**
===============================================================================
TARJETA CRC - tests/e2e/playwright.config.ts (Config Playwright E2E)
===============================================================================
Responsabilidades:
  - Configurar Playwright para E2E (local/CI).
  - Cargar envs E2E deterministas sin secretos.

Colaboradores:
  - tests/e2e/.env.e2e(.example)
  - tests/e2e/tests/*

Invariantes:
  - No imprimir secretos.
  - No modificar estado del repo.
===============================================================================
*/

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Configuration for RAG Corp E2E Tests
 *
 * @see https://playwright.dev/docs/test-configuration
 */
const CONFIG_DIR = path.dirname(fileURLToPath(import.meta.url));

function loadEnvFile(filePath: string) {
    if (!fs.existsSync(filePath)) return;
    const content = fs.readFileSync(filePath, "utf-8");
    for (const line of content.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const idx = trimmed.indexOf("=");
        if (idx <= 0) continue;
        const key = trimmed.slice(0, idx).trim();
        const value = trimmed.slice(idx + 1).trim();
        if (!process.env[key]) {
            process.env[key] = value;
        }
    }
}

loadEnvFile(path.join(CONFIG_DIR, ".env.e2e"));
loadEnvFile(path.join(CONFIG_DIR, ".env.e2e.example"));

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
