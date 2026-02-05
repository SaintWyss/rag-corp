/**
 * =============================================================================
 * TARJETA CRC - tests/e2e/tests/chat.spec.ts (E2E Chat)
 * =============================================================================
 * Responsabilidades:
 * - Validar chat sobre workspace accesible por empleado.
 * - Crear workspace vía admin y usar login de empleado en UI.
 *
 * Invariantes:
 * - No imprimir secretos.
 * =============================================================================
 */

import { expect, test } from "@playwright/test";
import {
  adminCreateWorkspaceForUserId,
  adminEnsureUser,
  adminGetUserIdByEmail,
  clearApiKeyStorage,
  hasAdminCredentials,
  login,
  loginAsAdmin,
} from "./helpers";

const EMP_USER = { email: "employee1@local", password: "employee1" };

test.describe("Chat flow", () => {
    const hasAdminEnv = hasAdminCredentials();

    test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

    test("sends a message and receives a response", async ({ page }) => {
        await clearApiKeyStorage(page);
        await loginAsAdmin(page);
        await adminEnsureUser(page, EMP_USER, "employee");
        const empId = await adminGetUserIdByEmail(page, EMP_USER.email);
        const workspaceName = `E2E WS ${Date.now()}`;
        const ws = await adminCreateWorkspaceForUserId(page, empId, workspaceName);

        await page.context().clearCookies();
        await login(page, EMP_USER.email, EMP_USER.password);
        await page.goto(`/workspaces/${ws.id}/chat`);
        await expect(page.getByTestId("chat-workspace")).toContainText(
            ws.id
        );

        const input = page.getByTestId("chat-input");
        await input.fill("Que es RAG?");

        const sendButton = page.getByTestId("chat-send-button");
        await sendButton.click();
        try {
            await expect(sendButton).toBeDisabled({ timeout: 1000 });
        } catch {
            // Si la respuesta es inmediata, el boton puede re-habilitarse rapido.
            await expect(sendButton).toBeEnabled();
        }

        const assistantMessage = page
            .locator('[data-testid="chat-message"][data-role="assistant"]')
            .last();

        await expect(assistantMessage).toHaveAttribute("data-status", "complete");
        await expect(assistantMessage).not.toHaveText("Generando...");
        await expect(sendButton).toBeEnabled();
    });
});
