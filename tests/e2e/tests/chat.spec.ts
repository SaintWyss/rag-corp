import { expect, test } from "@playwright/test";

test.describe("Chat flow", () => {
    const apiKey = process.env.TEST_API_KEY || "e2e-key";

    test.beforeEach(async ({ page }) => {
        await page.addInitScript((key) => {
            window.localStorage.setItem("ragcorp_api_key", key);
        }, apiKey);
        await page.goto("/chat");
    });

    test("sends a message and receives a response", async ({ page }) => {
        const input = page.getByTestId("chat-input");
        await input.fill("Que es RAG?");

        const sendButton = page.getByTestId("chat-send-button");
        await sendButton.click();
        await expect(sendButton).toBeDisabled();

        const assistantMessage = page
            .locator('[data-testid="chat-message"][data-role="assistant"]')
            .last();

        await expect(assistantMessage).toHaveAttribute("data-status", "complete");
        await expect(assistantMessage).not.toHaveText("Generando...");
        await expect(sendButton).toBeEnabled();
    });
});
