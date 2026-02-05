/**
 * =============================================================================
 * TARJETA CRC - tests/e2e/tests/admin-employee-flow.spec.ts (E2E Admin/Employee)
 * =============================================================================
 * Responsabilidades:
 * - Validar provisioning admin + acceso de empleado de punta a punta.
 * - Evitar flakes usando helpers de API para setup.
 *
 * Invariantes:
 * - No imprimir secretos.
 * =============================================================================
 */

import { expect, test } from "@playwright/test";
import {
  adminCreateWorkspaceForUserId,
  adminEnsureUser,
  adminListUsers,
  adminGetUserIdByEmail,
  clearApiKeyStorage,
  hasAdminCredentials,
  login,
  loginAsAdmin,
} from "./helpers";

// Support both seeded demo users and distinct CI users
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@local";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "admin";

const timestamp = Date.now();
const NEW_EMPLOYEE_EMAIL = `e2e-emp-${timestamp}@local`;
const NEW_EMPLOYEE_PASSWORD = "password123";
const NEW_WORKSPACE_NAME = `E2E Workspace ${timestamp}`;

test.describe.serial("Admin Provisioning & Employee Access", () => {
  const hasAdminEnv = hasAdminCredentials();
  test.skip(!hasAdminEnv, "E2E admin credentials are not configured.");

  test.beforeEach(async ({ page }) => {
    await clearApiKeyStorage(page);
  });

  test("Flow A: Admin creates user and workspace", async ({ page }) => {
    // 1. Admin login + setup via API (determinista)
    await loginAsAdmin(page);
    await adminEnsureUser(page, {
      email: NEW_EMPLOYEE_EMAIL,
      password: NEW_EMPLOYEE_PASSWORD,
    }, "employee");
    const empId = await adminGetUserIdByEmail(page, NEW_EMPLOYEE_EMAIL);
    await adminCreateWorkspaceForUserId(page, empId, NEW_WORKSPACE_NAME);

    // 2. Validar usuario y workspace via API (evita flakes de UI)
    const users = await adminListUsers(page);
    expect(users.some((u: any) => u.email === NEW_EMPLOYEE_EMAIL)).toBeTruthy();

    const wsRes = await page.request.get(`/api/admin/users/${empId}/workspaces`);
    expect(wsRes.ok()).toBeTruthy();
    const wsData = await wsRes.json();
    const wsList = wsData?.workspaces ?? [];
    expect(
      wsList.some((ws: any) => ws.name === NEW_WORKSPACE_NAME)
    ).toBeTruthy();
  });

  test("Flow B: Employee accesses workspace", async ({ page }) => {
    // 1. Employee Login
    await login(page, NEW_EMPLOYEE_EMAIL, NEW_EMPLOYEE_PASSWORD);
    
    // Should be redirected to /workspaces
    await expect(page).toHaveURL(/\/workspaces/);

    // 2. See workspace
    // Look for h3 with workspace name
    const wsLink = page.locator(`h3:text("${NEW_WORKSPACE_NAME}")`);
    await expect(wsLink).toBeVisible();
    
    // NOTE: Employees cannot see Publish/Archive/Share buttons.
    // Verify actions NOT present
    await expect(page.getByRole("button", { name: "Publicar" })).not.toBeVisible();

    // 3. Enter workspace
    // Use AppShell selector
    const workspaceSelector = page.getByTestId("workspace-selector");
    await expect(workspaceSelector).toBeVisible();
    await workspaceSelector.selectOption({ label: NEW_WORKSPACE_NAME });
    
    // Employee should land in documents
    // Note: The URL usually includes the UUID, so we regex match
    await expect(page).toHaveURL(/\/workspaces\/.*\/documents/);

    // Read-only UI should exist
    await expect(page.getByTestId("sources-refresh")).toBeVisible();
    await expect(page.getByText("Sources (solo lectura)")).toBeVisible();

    // Upload UI must NOT exist for employee
    await expect(page.getByTestId("sources-upload-form")).toHaveCount(0);
    await expect(page.getByTestId("sources-title-input")).toHaveCount(0);
    await expect(page.getByTestId("sources-file-input")).toHaveCount(0);
    await expect(page.getByTestId("sources-upload-submit")).toHaveCount(0);

    // Logout (App Shell now has "Logout")
    await page.getByRole("link", { name: "Logout" }).click();
  });

  test("Flow C: Negative Access Controls", async ({ page }) => {
    // 1. Employee tries Admin Route
    await login(page, NEW_EMPLOYEE_EMAIL, NEW_EMPLOYEE_PASSWORD);
    await page.goto("/admin/users");
    // Should redirect to /workspaces
    await expect(page).toHaveURL(/\/workspaces/);
    
    // Logout
    await page.getByRole("link", { name: "Logout" }).click();
    
    // 2. Admin tries Employee Route (direct access)
    // Admin CAN access /workspaces? 
    // ADR-008: Admin: si intenta /workspaces or /workspaces/* => redirect /admin/users
    await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
    await page.goto("/workspaces").catch(() => null);
    await expect(page).toHaveURL(/\/admin\/users/);
  });
});
