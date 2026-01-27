import { expect, test, type Page } from "@playwright/test";
import { clearApiKeyStorage, login } from "./helpers";

const ADMIN_USER = { email: "admin@local", password: "admin" };
const EMP1_USER = { email: "employee1@local", password: "employee1" };
const EMP2_USER = { email: "employee2@local", password: "employee2" };

test.describe.serial("Role Separation & Isolation", () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    try {
        await login(page, ADMIN_USER.email, ADMIN_USER.password);
        await ensureUserExists(page, EMP1_USER);
        await ensureUserExists(page, EMP2_USER);
    } catch (e) {
        console.error("Setup failed:", e);
        throw e;
    } finally {
        await page.close();
    }
  });

  test.beforeEach(async ({ page }) => {
    await clearApiKeyStorage(page);
  });

  async function ensureUserExists(page: Page, user: {email: string, password: string}) {
      await page.goto("/admin/users");
      
      // Wait for table of users to be ready (api call to list users)
      // We assume the page fetches users on mount.
      // Let's waitForResponse for GET users if possible, or just wait for network idle state.
      // Simple robustness: Wait for any row OR timeout.
      try {
        await page.locator('[data-testid="admin-users-row"]').first().waitFor({ state: "visible", timeout: 2000 });
      } catch {
        // List might be empty, continue.
      }

      // Check if user exists in the list
      const userRow = page.locator(`[data-testid="admin-users-row"]`, { hasText: user.email });
      
      if (await userRow.count() > 0) {
          console.log(`User ${user.email} already visible.`);
          return;
      }
      
      console.log(`Seeding user ${user.email}...`);
      await page.getByPlaceholder("empleado@ragcorp.com").fill(user.email);
      await page.getByPlaceholder("Min 8 caracteres").fill(user.password);
      await page.locator("select").first().selectOption("employee");
      
      // A) waitForResponse del POST real
      const createPromise = page.waitForResponse(resp => 
        resp.url().includes("/users") && resp.request().method() === "POST"
      );

      await page.getByRole("button", { name: "Crear usuario" }).click();
      
      // B) assert status 2xx; si no, loggear status + response text
      const response = await createPromise;
      if (!response.ok()) {
          if (response.status() === 409) {
              console.log(`User ${user.email} already exists (409 Conflict). Reloading to verify.`);
              await page.reload();
              
              // Robustness: Check if we were redirected to login (session lost)
              if (page.url().includes("/login")) {
                  console.log("Session lost during reload. Re-logging in as Admin...");
                  await login(page, ADMIN_USER.email, ADMIN_USER.password);
                  await page.goto("/admin/users");
              }

              // Wait for table to load again
              try {
                await page.locator('[data-testid="admin-users-row"]').first().waitFor({ state: "visible", timeout: 3000 });
              } catch {
                console.log("Admin users table did not populate rows immediately.");
              }
              
              const userRow = page.locator(`[data-testid="admin-users-row"]`, { hasText: user.email });
              const visibleRows = await page.locator('[data-testid="admin-users-row"]').allTextContents();
              console.log(`DEBUG: Visible rows for ${user.email} check:`, visibleRows);
              
              // Verify visibility with a retry
              await expect(userRow).toBeVisible({ timeout: 10000 });
              return;
          }
          const body = await response.text();
          throw new Error(`Failed to create user ${user.email}. Status: ${response.status()} Body: ${body}`);
      }
      
      // C) esperar UI update
      await expect(userRow).toBeVisible();
  }

  test("Admin Capabilities: Can access Workspaces and Create Panel", async ({ page }) => {
    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    
    // Default landing should be Admin Console
    await expect(page).toHaveURL(/\/admin\/users/);

    // Navigating to Workspaces should be ALLOWED
    await page.goto("/workspaces");
    await expect(page).toHaveURL(/\/workspaces/);
    
    // Debug: Check what role the UI thinks we have
    const roleBadge = page.getByTestId("workspaces-role");
    await expect(roleBadge).not.toHaveText("Verificando", { timeout: 10000 });
    console.log("Role Label:", await roleBadge.textContent());
    
    await expect(roleBadge).toHaveText("Admin");
    
    // Admin should see the creation panel
    await expect(page.getByTestId("workspaces-create-panel")).toBeVisible();
  });

  test("Employee Redirection: Cannot access Admin Console", async ({ page }) => {
    await login(page, EMP1_USER.email, EMP1_USER.password);

    // Default landing should be Workspaces
    await expect(page).toHaveURL(/\/workspaces/);
    
    // Check UI has no admin links (e.g. users management)
    // Note: AppShell doesn't show admin links by default, but checking anyway.
    await expect(page.getByRole("link", { name: "Users" })).not.toBeVisible();

    // Try forcing URL to Admin Console
    await page.goto("/admin/users");
    // Should be redirected to /workspaces
    await expect(page).toHaveURL(/\/workspaces/);
  });

  test("Employee Isolation: Cannot see or access other employee's workspace", async ({ page }) => {
    // 1. Setup: Admin creates private workspace for Employee 2
    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto("/admin/workspaces");

    const targetName = `Private Space Emp2 ${Date.now()}`;
    
    // Select Emp2
    const userSelect = page.getByTestId("admin-workspaces-user-select");
    await userSelect.selectOption({ label: `${EMP2_USER.email} (employee)` });
    
    await page.getByTestId("admin-workspaces-name-input").fill(targetName);
    // Visibility defaults to private
    await page.getByTestId("admin-workspaces-submit").click();
    
    // Wait for creation and capture ID
    const card = page.locator(`[data-testid^="workspace-card-"]`, { hasText: targetName });
    await expect(card).toBeVisible();
    
    // Extract ID from testid
    const testId = await card.getAttribute("data-testid");
    const targetId = testId?.replace("workspace-card-", "");
    expect(targetId).toBeTruthy();

    await page.getByRole("link", { name: "Cerrar sesión" }).click();

    // 2. Login as Employee 1
    await login(page, EMP1_USER.email, EMP1_USER.password);
    await expect(page).toHaveURL(/\/workspaces/);

    // 3. Verify not visible in selectors
    // Check empty state or selector content
    // We expect Selector to NOT have targetName
    const workspaceSelector = page.getByTestId("workspace-selector");
    
    // Check options text
    const optionsText = await workspaceSelector.textContent();
    expect(optionsText).not.toContain(targetName);

    // 4. Try direct access (IDOR attempt)
    // Visit /workspaces/[targetId]/documents
    // Backend should return 403 Forbidden
    // Since AppShell handles errors, we might see global error banner or redirect?
    // Using API check: listWorkspaces would return error or empty list 
    
    // Visit page:
    await page.goto(`/workspaces/${targetId}/documents`);
    
    // Two possible successful outcomes defining "secure":
    // A. 404/403 displayed in UI
    // B. Redirected to /workspaces root because it's not found/allowed
    
    // Our AppShell useEffect says: if pathname is documents/chat replace /workspaces.
    // Workspace load is async.
    // If listWorkspaces fails/returns empty, visibleWorkspaces is empty.
    
    // Check for "Error: Access denied" or similar in UI status banner if handled
    // Or check redirection if the app logic force-redirects invalid IDs.
    
    // Let's inspect the page content for access checking
    // Wait a bit for load
    await page.waitForTimeout(1000); 

    // We expect either being at /workspaces (redirected) OR seeing an error message
    // If the URL remains on the target, verify content is blocked
    const url = page.url();
    if (url.includes(`/workspaces/${targetId}`)) {
        // We are still on the page. Content should be hidden or error shown.
        // AppShell shows "No hay workspaces visibles" in selector if list empty.
        // Content area shows "Cargando..." or nothing?
        // Actually, if workspaceId is not in valid list, the selector won't select it.
        // And the Documents view would fail to load documents (403 on API).
        
        // Check for error banner
        // Let's try to verify we CANNOT see "Sources" list for that workspace.
        await expect(page.getByTestId("documents-list")).not.toBeVisible();
    } else {
        // Redirected is also safe
        expect(url).toContain("/workspaces");
    }
  });
});
