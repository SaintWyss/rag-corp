import { expect, test } from "@playwright/test";

test.describe("Documents flow", () => {
    const apiKey = process.env.TEST_API_KEY || "e2e-key";

    test.beforeEach(async ({ page }) => {
        await page.addInitScript((key) => {
            window.localStorage.setItem("ragcorp_api_key", key);
        }, apiKey);
        await page.goto("/documents");
    });

    test("ingest -> list -> detail -> delete", async ({ page }) => {
        const docTitle = `E2E Document ${Date.now()}`;
        const docText =
            "Este documento de prueba valida la ingesta y el CRUD desde la UI.";

        const titleInput = page.locator(
            '[data-testid="documents-title-input"][data-draft-index="0"]'
        );
        const textInput = page.locator(
            '[data-testid="documents-text-input"][data-draft-index="0"]'
        );

        await titleInput.fill(docTitle);
        await textInput.fill(docText);

        await page.getByTestId("documents-ingest-submit").click();

        const listItem = page.locator(
            `[data-testid="document-list-item"][data-document-title="${docTitle}"]`
        );
        await expect(listItem).toBeVisible();
        await listItem.click();

        await expect(page.getByTestId("document-detail")).toHaveAttribute(
            "data-document-title",
            docTitle
        );

        page.once("dialog", (dialog) => dialog.accept());
        await page.getByTestId("document-delete-button").click();

        await expect(
            page.locator(
                `[data-testid="document-list-item"][data-document-title="${docTitle}"]`
            )
        ).toHaveCount(0);
    });
});
