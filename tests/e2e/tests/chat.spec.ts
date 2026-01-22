import { expect, test } from "@playwright/test";
import { createWorkspace, setSessionApiKey } from "./helpers";

test.describe("Chat flow", () => {
    const apiKey = process.env.TEST_API_KEY || "e2e-key";

    test.beforeEach(async ({ page }) => {
        await setSessionApiKey(page, apiKey);
        await page.goto("/chat");
        await expect(page).toHaveURL(/\/workspaces$/);
        await expect(page.getByTestId("workspaces-page")).toBeVisible();
    });

    test("sends a message and receives a response", async ({ page }) => {
        const workspaceName = `E2E WS ${Date.now()}`;
        const workspaceId = await createWorkspace(page, workspaceName);
        await page.goto(`/workspaces/${workspaceId}/chat`);
        await expect(page.getByTestId("chat-workspace")).toContainText(
            workspaceId
        );

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
