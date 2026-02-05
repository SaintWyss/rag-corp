/**
===============================================================================
TARJETA CRC - tests/e2e/playwright.config.cjs (Config Playwright E2E)
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

const fs = require("node:fs");
const path = require("node:path");
const { defineConfig, devices } = require("@playwright/test");

const CONFIG_DIR = __dirname;

function loadEnvFile(filePath) {
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

module.exports = defineConfig({
  testDir: "./tests",
  fullyParallel: !useCompose && !process.env.CI,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : useCompose ? 1 : undefined,
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

  /* Configure dev server when not using Compose */
  webServer: useCompose
    ? undefined
    : {
        command: "pnpm -C apps/frontend dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
