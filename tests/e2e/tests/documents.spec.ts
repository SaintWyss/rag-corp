import path from "path";
import { expect, test } from "@playwright/test";
import { createWorkspace, hasAdminCredentials, loginAsAdmin } from "./helpers";

test.describe("Sources flow", () => {
    const hasAdminEnv = hasAdminCredentials();

    test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
        await page.goto("/workspaces");
        await expect(page).toHaveURL(/\/workspaces$/);
        await expect(page.getByTestId("workspaces-page")).toBeVisible();
    });

    test("upload -> list -> detail -> ready", async ({ page }) => {
        const workspaceName = `E2E WS ${Date.now()}`;
        const workspaceId = await createWorkspace(page, workspaceName);
        await page.goto(`/workspaces/${workspaceId}/documents`);
        await expect(page.getByTestId("sources-workspace")).toContainText(
            workspaceId
        );

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

        await expect
            .poll(
                async () => {
                    await page.getByTestId("sources-refresh").click();
                    return (await status.textContent()) || "";
                },
                { timeout: 60_000 }
            )
            .toContain("READY");
    });
});
