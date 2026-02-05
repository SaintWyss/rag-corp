/**
 * =============================================================================
 * TARJETA CRC - tests/e2e/tests/full-pipeline.spec.ts (E2E Pipeline)
 * =============================================================================
 * Responsabilidades:
 * - Validar upload + procesamiento + chat en workspace de empleado.
 * - Admin crea workspace y sube documento; empleado consume.
 *
 * Invariantes:
 * - No imprimir secretos.
 * =============================================================================
 */

import path from "path";
import { expect, test } from "@playwright/test";
import {
  adminCreateWorkspaceForUserId,
  adminEnsureUser,
  adminGetUserIdByEmail,
  clearApiKeyStorage,
  hasAdminCredentials,
  login,
  loginAsAdmin,
  uploadDocumentAndWaitReady,
} from "./helpers";

const EMP_USER = { email: "employee1@local", password: "employee1" };

test.describe("Full pipeline", () => {
    const hasAdminEnv = hasAdminCredentials();
    test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

    test("upload -> ready -> chat streaming", async ({ page }) => {
        await clearApiKeyStorage(page);
        await loginAsAdmin(page);
        await adminEnsureUser(page, EMP_USER, "employee");
        const empId = await adminGetUserIdByEmail(page, EMP_USER.email);

        const docTitle = `Pipeline ${Date.now()}`;
        const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");
        const workspaceName = `E2E Workspace ${Date.now()}`;
        const ws = await adminCreateWorkspaceForUserId(page, empId, workspaceName);
        await uploadDocumentAndWaitReady(page, ws.id, docTitle, filePath);

        await page.context().clearCookies();
        await login(page, EMP_USER.email, EMP_USER.password);
        await page.goto(`/workspaces/${ws.id}/chat`);

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
