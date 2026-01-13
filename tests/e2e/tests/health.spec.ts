import { expect, test } from "@playwright/test";

/**
 * E2E Tests: Health and Basic Connectivity
 *
 * These tests verify that the basic infrastructure is working.
 */

test.describe("Health Checks", () => {
    test("backend API is healthy", async ({ request }) => {
        const response = await request.get("http://localhost:8000/healthz");
        expect(response.ok()).toBeTruthy();

        const body = await response.json();
        expect(body.ok).toBe(true);
        expect(body.db).toBe("connected");
    });

    test("backend metrics endpoint is accessible", async ({ request }) => {
        const response = await request.get("http://localhost:8000/metrics");
        expect(response.ok()).toBeTruthy();
    });

    test("frontend loads successfully", async ({ page }) => {
        await page.goto("/");
        // Verify the page title or main heading
        await expect(page).toHaveTitle(/RAG/i);
    });
});
