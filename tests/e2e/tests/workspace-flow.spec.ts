import path from "path";
import { expect, test, type Page } from "@playwright/test";

const adminEmail = process.env.E2E_ADMIN_EMAIL || "admin@example.com";
const adminPassword = process.env.E2E_ADMIN_PASSWORD || "admin-pass-123";
const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");

async function loginAsAdmin(page: Page) {
    const response = await page.request.post("/auth/login", {
        data: { email: adminEmail, password: adminPassword },
    });
    expect(response.ok()).toBeTruthy();
}

async function createWorkspace(page: Page, name: string): Promise<string> {
    await page.goto("/workspaces");
    await expect(page.getByTestId("workspaces-create-form")).toBeVisible();

    await page.getByTestId("workspaces-create-name").fill(name);
    await page.getByTestId("workspaces-create-submit").click();

    const card = page.locator('[data-testid^="workspace-card-"]', {
        hasText: name,
    });
    await expect(card).toBeVisible();

    const testId = await card.getAttribute("data-testid");
    expect(testId).toBeTruthy();
    return testId?.replace("workspace-card-", "") || "";
}

async function uploadDocumentAndWaitReady(
    page: Page,
    workspaceId: string,
    title: string
): Promise<string> {
    await page.goto(`/workspaces/${workspaceId}/documents`);
    await expect(page.getByTestId("sources-workspace")).toContainText(workspaceId);

    await page.getByTestId("sources-title-input").fill(title);
    await page.getByTestId("sources-file-input").setInputFiles(filePath);
    await page.getByTestId("sources-upload-submit").click();

    const listItem = page.locator('[data-testid="source-list-item"]', {
        hasText: title,
    });
    await expect(listItem).toBeVisible();
    await listItem.click();

    const detail = page.getByTestId("source-detail");
    await expect(detail).toHaveAttribute("data-document-title", title);

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

    const docId = await detail.getAttribute("data-document-id");
    expect(docId).toBeTruthy();
    return docId || "";
}

test.describe("Workspace v4 flow", () => {
    test("create -> upload -> ready -> chat scoped sources", async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.removeItem("ragcorp_api_key");
        });

        await loginAsAdmin(page);

        const workspaceName = `E2E Workspace ${Date.now()}`;
        const workspaceId = await createWorkspace(page, workspaceName);
        expect(workspaceId).not.toBe("");

        const docTitle = `E2E Doc ${Date.now()}`;
        const docId = await uploadDocumentAndWaitReady(
            page,
            workspaceId,
            docTitle
        );

        const otherWorkspaceName = `E2E Workspace ${Date.now()}-B`;
        const otherWorkspaceId = await createWorkspace(page, otherWorkspaceName);
        expect(otherWorkspaceId).not.toBe("");

        const otherDocTitle = `E2E Doc ${Date.now()}-B`;
        const otherDocId = await uploadDocumentAndWaitReady(
            page,
            otherWorkspaceId,
            otherDocTitle
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
