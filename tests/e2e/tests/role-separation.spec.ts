/**
 * =============================================================================
 * TARJETA CRC - tests/e2e/tests/role-separation.spec.ts (E2E Roles)
 * =============================================================================
 * Responsabilidades:
 * - Validar separación de roles y redirecciones admin/employee.
 * - Usar credenciales E2E configurables por env.
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

const ADMIN_USER = {
  email: process.env.E2E_ADMIN_EMAIL || "admin@local",
  password: process.env.E2E_ADMIN_PASSWORD || "admin",
};
const EMP1_USER = { email: "employee1@local", password: "employee1" };
const EMP2_USER = { email: "employee2@local", password: "employee2" };

let targetWorkspaceId = "";
let targetWorkspaceName = "";

test.describe.serial("Role Separation & Isolation", () => {
  const hasAdminEnv = hasAdminCredentials();
  test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
      console.log("Starting Setup: Seeding users and workspaces via API...");

      await loginAsAdmin(page);

      await adminEnsureUser(page, EMP1_USER, "employee");
      await adminEnsureUser(page, EMP2_USER, "employee");

      const emp2Id = await adminGetUserIdByEmail(page, EMP2_USER.email);
      console.log(`Employee 2 ID: ${emp2Id}`);

      targetWorkspaceName = `Private Space Emp2 ${Date.now()}`;
      const ws = await adminCreateWorkspaceForUserId(
        page,
        emp2Id,
        targetWorkspaceName,
        "Secret stuff"
      );

      targetWorkspaceId = ws.id;
      console.log(
        `Created Target Workspace: ${targetWorkspaceId} (${targetWorkspaceName})`
      );
    } finally {
      await page.close();
      await context.close();
    }
  });

  test.beforeEach(async ({ page }) => {
    await clearApiKeyStorage(page);
  });

  test("Admin Redirection: Cannot access Employee Portal", async ({ page }) => {
    await login(page, ADMIN_USER.email, ADMIN_USER.password);

    await expect(page).toHaveURL(/\/admin\/users/);

    await page
      .goto("/workspaces", { waitUntil: "domcontentloaded" })
      .catch(() => null);
    await expect(page).toHaveURL(/\/admin\/users/, { timeout: 15_000 });
  });

  test("Employee Redirection: Cannot access Admin Console", async ({ page }) => {
    await login(page, EMP1_USER.email, EMP1_USER.password);

    await expect(page).toHaveURL(/\/workspaces/);

    await page
      .goto("/admin/users", { waitUntil: "domcontentloaded" })
      .catch(() => null);
    await expect(page).toHaveURL(/\/workspaces/, { timeout: 15_000 });
  });

  test("Employee Isolation: Cannot see or access other employee's workspace", async ({
    page,
  }) => {
    await login(page, EMP1_USER.email, EMP1_USER.password);
    await expect(page).toHaveURL(/\/workspaces/);

    const selector = page.getByTestId("workspace-selector");
    await expect(selector).toBeVisible({ timeout: 15_000 });

    const content = (await selector.textContent()) || "";
    expect(content).not.toContain(targetWorkspaceName);

    const card = page.locator(`[data-testid^="workspace-card-"]`, {
      hasText: targetWorkspaceName,
    });
    await expect(card).toHaveCount(0);

    const apiRes = await page.request.get(
      `/api/workspaces/${targetWorkspaceId}/documents`
    );
    expect([403, 404]).toContain(apiRes.status());

    await page.goto(`/workspaces/${targetWorkspaceId}/documents`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page).not.toHaveURL(/\/login/);
  });
});
