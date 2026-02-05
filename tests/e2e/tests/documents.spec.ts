/**
 * =============================================================================
 * TARJETA CRC - tests/e2e/tests/documents.spec.ts (E2E Sources)
 * =============================================================================
 * Responsabilidades:
 * - Validar listado/detalle de fuentes para un empleado.
 * - Subir documento via API admin (sin UI) y verificar READY en UI.
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

test.describe("Sources flow", () => {
    const hasAdminEnv = hasAdminCredentials();

    test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

    test("upload -> list -> detail -> ready", async ({ page }) => {
        await clearApiKeyStorage(page);
        await loginAsAdmin(page);
        await adminEnsureUser(page, EMP_USER, "employee");
        const empId = await adminGetUserIdByEmail(page, EMP_USER.email);
        const workspaceName = `E2E WS ${Date.now()}`;
        const ws = await adminCreateWorkspaceForUserId(page, empId, workspaceName);

        const docTitle = `Source ${Date.now()}`;
        const filePath = path.join(__dirname, "..", "fixtures", "sample.pdf");
        await uploadDocumentAndWaitReady(page, ws.id, docTitle, filePath);

        await page.context().clearCookies();
        await login(page, EMP_USER.email, EMP_USER.password);
        await page.goto(`/workspaces/${ws.id}/documents`);
        await expect(page.getByTestId("sources-workspace")).toContainText(ws.id);

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
