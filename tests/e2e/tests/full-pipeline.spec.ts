import path from "path";
import { expect, test, type Page } from "@playwright/test";

const adminEmail = process.env.E2E_ADMIN_EMAIL || "admin@example.com";
const adminPassword = process.env.E2E_ADMIN_PASSWORD || "admin-pass-123";

async function loginAsAdmin(page: Page) {
    const response = await page.request.post("/auth/login", {
        data: { email: adminEmail, password: adminPassword },
    });
    expect(response.ok()).toBeTruthy();
}

test.describe("Full pipeline", () => {
    test("upload -> ready -> chat streaming", async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.removeItem("ragcorp_api_key");
        });

        await loginAsAdmin(page);

        await page.goto("/documents");

        const docTitle = `Pipeline ${Date.now()}`;
        const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");

        await page.getByTestId("sources-title-input").fill(docTitle);
        await page.getByTestId("sources-file-input").setInputFiles(filePath);
        await page.getByTestId("sources-upload-submit").click();

        const listItem = page.locator(
            `[data-testid="source-list-item"][data-document-title="${docTitle}"]`
        );
        await expect(listItem).toBeVisible();
        await listItem.click();

        const status = page.getByTestId("source-detail-status");
        await expect(status).toBeVisible();

        for (let i = 0; i < 15; i += 1) {
            const text = (await status.textContent()) || "";
            if (text.includes("READY")) {
                break;
            }
            await page.getByTestId("sources-refresh").click();
            await page.waitForTimeout(2000);
        }

        await expect(status).toHaveText(/READY/);

        await page.goto("/chat");

        const input = page.getByTestId("chat-input");
        await input.fill("Resume el documento cargado.");
        await page.getByTestId("chat-send-button").click();

        const assistantMessage = page
            .locator('[data-testid="chat-message"][data-role="assistant"]')
            .last();
        await expect(assistantMessage).toHaveAttribute("data-status", "complete");
        await expect(assistantMessage).not.toHaveText("Generando...");
    });
});
