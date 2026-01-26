import { expect, test, type Page } from "@playwright/test";
import { clearApiKeyStorage } from "./helpers";
const fs = require("fs");

// Support both seeded demo users and distinct CI users
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@local";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "admin";

const timestamp = Date.now();
const NEW_EMPLOYEE_EMAIL = `e2e-emp-${timestamp}@local`;
const NEW_EMPLOYEE_PASSWORD = "password123";
const NEW_WORKSPACE_NAME = `E2E Workspace ${timestamp}`;

// Helper login function
async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByPlaceholder("name@example.com").fill(email);
  await page.getByPlaceholder("••••••••").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  // Wait for login to complete (redirect away from login)
  await page.waitForURL((url) => !url.pathname.includes("/login"));
}

test.describe.serial("Admin Provisioning & Employee Access", () => {
  test.beforeEach(async ({ page }) => {
    await clearApiKeyStorage(page);
  });

  test("Flow A: Admin creates user and workspace", async ({ page }) => {
    // 1. Admin Login
    await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
    await expect(page).toHaveURL(/\/admin\/users/);

    // 2. Create Employee
    await page.getByPlaceholder("empleado@ragcorp.com").fill(NEW_EMPLOYEE_EMAIL);
    await page.getByPlaceholder("Min 8 caracteres").fill(NEW_EMPLOYEE_PASSWORD);
    
    // Select role (default is employee, explicit check for robustness)
    const roleSelect = page.locator("select").nth(0);
    await roleSelect.selectOption("employee");
    
    await page.getByRole("button", { name: "Crear usuario" }).click();
    
    // Validate user created in list
    const userRow = page.locator(`[data-testid="admin-users-row"]`, { hasText: NEW_EMPLOYEE_EMAIL });
    await expect(userRow).toBeVisible();

    // 3. Go to Workspaces Provisioning
    await page.getByRole("link", { name: "Workspaces" }).click();
    await expect(page).toHaveURL(/\/admin\/workspaces/);

    // 4. Create Workspace for new Employee
    const userSelect = page.getByTestId("admin-workspaces-user-select");
    await expect(userSelect).toBeVisible();
    
    // Wait for options to load (react query async)
    await expect(userSelect.locator(`option`)).not.toHaveCount(1); // More than just default
    
    // Select by label logic
    await userSelect.selectOption({ label: `${NEW_EMPLOYEE_EMAIL} (employee)` });

    // Fill workspace form
    await page.getByTestId("admin-workspaces-name-input").fill(NEW_WORKSPACE_NAME);
    
    await page.getByTestId("admin-workspaces-submit").click();

    // Debug: Check for success or error
    try {
        await expect(page.getByText(`Workspace creado: ${NEW_WORKSPACE_NAME}`)).toBeVisible({ timeout: 5000 });
    } catch (e) {
        console.log("Success message not found. Checking for errors...");
        const errorMsg = await page.getByTestId("status-banner-error").textContent().catch(() => "No error banner found"); // Assuming ID or use text
        const pageText = (await page.textContent("body")) || "";
        console.log(`Page text dump: ${pageText.slice(0, 500)}...`); 
        throw new Error(`Workspace creation failed. Error visible: ${await page.locator('.text-rose-400, .bg-rose-500').allTextContents()}`);
    }

    // 5. Validate Workspace in list (Right column)
    const wsCard = page.locator(`h3:text("${NEW_WORKSPACE_NAME}")`);
    await expect(wsCard).toBeVisible();
    
    // Logout (Admin Shell has "Cerrar sesión")
    await page.getByRole("link", { name: "Cerrar sesión" }).click();
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
    await page.goto("/workspaces");
    await expect(page).toHaveURL(/\/admin\/users/);
  });
});
