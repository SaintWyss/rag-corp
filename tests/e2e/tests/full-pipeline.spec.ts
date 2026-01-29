import path from "path";
import { expect, test } from "@playwright/test";
import {
    clearApiKeyStorage,
    createWorkspace,
    hasAdminCredentials,
    loginAsAdmin,
    uploadDocumentAndWaitReady,
} from "./helpers";

test.describe("Full pipeline", () => {
    const hasAdminEnv = hasAdminCredentials();
    test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

    test("upload -> ready -> chat streaming", async ({ page }) => {
        await clearApiKeyStorage(page);
        await loginAsAdmin(page);

        const docTitle = `Pipeline ${Date.now()}`;
        const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");
        const workspaceName = `E2E Workspace ${Date.now()}`;
        const workspaceId = await createWorkspace(page, workspaceName);
        await uploadDocumentAndWaitReady(page, workspaceId, docTitle, filePath);

        await page.goto(`/workspaces/${workspaceId}/chat`);

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
