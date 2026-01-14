import path from "path";
import { expect, test } from "@playwright/test";

test.describe("Sources flow", () => {
    const apiKey = process.env.TEST_API_KEY || "e2e-key";

    test.beforeEach(async ({ page }) => {
        await page.addInitScript((key) => {
            window.localStorage.setItem("ragcorp_api_key", key);
        }, apiKey);
        await page.goto("/documents");
    });

    test("upload -> list -> detail -> ready", async ({ page }) => {
        const docTitle = `Source ${Date.now()}`;
        const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");

        await page.getByTestId("sources-title-input").fill(docTitle);
        await page.getByTestId("sources-file-input").setInputFiles(filePath);
        await page.getByTestId("sources-upload-submit").click();

        const listItem = page.locator(
            `[data-testid="source-list-item"][data-document-title="${docTitle}"]`
        );
        await expect(listItem).toBeVisible();
        await listItem.click();

        await expect(page.getByTestId("source-detail")).toHaveAttribute(
            "data-document-title",
            docTitle
        );

        const status = page.getByTestId("source-detail-status");
        await expect(status).toBeVisible();

        for (let i = 0; i < 12; i += 1) {
            const text = (await status.textContent()) || "";
            if (text.includes("READY")) {
                break;
            }
            await page.getByTestId("sources-refresh").click();
            await page.waitForTimeout(2000);
        }

        await expect(status).toHaveText(/READY/);
    });
});
