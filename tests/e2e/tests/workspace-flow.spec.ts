import { expect, test } from "@playwright/test";
import path from "path";
import {
    adminCreateWorkspaceForUserId,
    adminEnsureUser,
    adminGetUserIdByEmail,
    clearApiKeyStorage,
    hasAdminCredentials,
    login,
    loginAsAdmin,
    uploadDocumentAndWaitReady
} from "./helpers";

const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");
const EMP_USER = { email: "employee1@local", password: "employee1" };
const ADMIN_USER = { email: "admin@local", password: "admin" };

test.describe("Workspace v4 flow", () => {
    const hasAdminEnv = hasAdminCredentials();
    test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

    test("create (via admin) -> upload (as employee) -> ready -> chat scoped sources", async ({ page }) => {
        await clearApiKeyStorage(page);
        
        // 1. Setup: Admin creates workspaces for Employee
        // We use a separate context or just API calls via page.request
        // Since helper loginAsAdmin uses page.request, it sets cookies on current context.
        // We might want to clear cookies after admin operations or just use them purely for API.
        
        let empUserId: string;
        
        // Admin operations
        {
            await loginAsAdmin(page);
            
            // Ensure employee exists
            // This is safer than assuming it exists from other tests
            await adminEnsureUser(page, EMP_USER);

            // Get Employee ID
            empUserId = await adminGetUserIdByEmail(page, EMP_USER.email);
        }

        // Create Workspace A
        const workspaceName = `E2E Workspace ${Date.now()}`;
        const wsA = await adminCreateWorkspaceForUserId(page, empUserId, workspaceName);
        const workspaceId = wsA.id;
        expect(workspaceId).toBeTruthy();

        // Create Workspace B
        const otherWorkspaceName = `E2E Workspace ${Date.now()}-B`;
        const wsB = await adminCreateWorkspaceForUserId(page, empUserId, otherWorkspaceName);
        const otherWorkspaceId = wsB.id;
        expect(otherWorkspaceId).toBeTruthy();

        // 2. Login as Employee to use the workspace
        // Clear admin cookies first? login() overwrites them but clearer to be safe.
        await page.context().clearCookies();
        await login(page, EMP_USER.email, EMP_USER.password);

        // 3. Employee uploads documents
        const docTitle = `E2E Doc ${Date.now()}`;
        const docId = await uploadDocumentAndWaitReady(
            page,
            workspaceId,
            docTitle,
            filePath
        );

        const otherDocTitle = `E2E Doc ${Date.now()}-B`;
        const otherDocId = await uploadDocumentAndWaitReady(
            page,
            otherWorkspaceId,
            otherDocTitle,
            filePath
        );

        // 4. Chat interactions
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
