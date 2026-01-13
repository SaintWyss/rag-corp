import { expect, test } from "@playwright/test";

/**
 * E2E Tests: Frontend UI
 *
 * These tests verify the frontend user interface works correctly.
 */

test.describe("Frontend UI", () => {
    test.beforeEach(async ({ page }) => {
        await page.goto("/");
    });

    test("shows main heading", async ({ page }) => {
        // Look for a heading that indicates we're on the RAG app
        const heading = page.locator("h1, h2").first();
        await expect(heading).toBeVisible();
    });

    test("has a query input field", async ({ page }) => {
        // Look for an input or textarea for queries
        const input = page.locator('input[type="text"], textarea').first();
        await expect(input).toBeVisible();
    });

    test("can type a question", async ({ page }) => {
        const input = page.locator('input[type="text"], textarea').first();
        await input.fill("What is RAG?");
        await expect(input).toHaveValue("What is RAG?");
    });

    test("has a submit button", async ({ page }) => {
        // Look for a button to submit queries
        const button = page.locator('button[type="submit"], button:has-text("Ask"), button:has-text("Search"), button:has-text("Send")').first();
        await expect(button).toBeVisible();
    });
});
