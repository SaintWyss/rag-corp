import path from "path";
import { expect, test } from "@playwright/test";
import {
    clearApiKeyStorage,
    createWorkspace,
    loginAsAdmin,
    uploadDocumentAndWaitReady,
} from "./helpers";

const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");

test.describe("Workspace v4 flow", () => {
    test("create -> upload -> ready -> chat scoped sources", async ({ page }) => {
        await clearApiKeyStorage(page);
        await loginAsAdmin(page);

        const workspaceName = `E2E Workspace ${Date.now()}`;
        const workspaceId = await createWorkspace(page, workspaceName);
        expect(workspaceId).not.toBe("");

        const docTitle = `E2E Doc ${Date.now()}`;
        const docId = await uploadDocumentAndWaitReady(
            page,
            workspaceId,
            docTitle,
            filePath
        );

        const otherWorkspaceName = `E2E Workspace ${Date.now()}-B`;
        const otherWorkspaceId = await createWorkspace(page, otherWorkspaceName);
        expect(otherWorkspaceId).not.toBe("");

        const otherDocTitle = `E2E Doc ${Date.now()}-B`;
        const otherDocId = await uploadDocumentAndWaitReady(
            page,
            otherWorkspaceId,
            otherDocTitle,
            filePath
        );

        await page.goto(`/workspaces/${workspaceId}/chat`);
        await expect(page.getByTestId("chat-workspace")).toContainText(
            workspaceId
        );

        const input = page.getByTestId("chat-input");
        await input.fill("Resume el documento cargado.");
        await page.getByTestId("chat-send-button").click();

        const assistantMessage = page
            .locator('[data-testid="chat-message"][data-role="assistant"]')
            .last();
        await expect(assistantMessage).toHaveAttribute("data-status", "complete");

        const verifiedSources = page.getByTestId("chat-verified-source");
        await expect(verifiedSources.first()).toBeVisible();

        const sourceTexts = await verifiedSources.allTextContents();
        const hasWorkspaceDoc = sourceTexts.some((text) =>
            text.includes(docId)
        );
        const hasOtherDoc = sourceTexts.some((text) =>
            text.includes(otherDocId)
        );

        expect(hasWorkspaceDoc).toBeTruthy();
        expect(hasOtherDoc).toBeFalsy();
    });
});
