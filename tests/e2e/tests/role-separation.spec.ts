import { expect, test, type Page } from "@playwright/test";
import {
    adminCreateWorkspaceForUserId,
    adminGetUserIdByEmail,
    clearApiKeyStorage,
    login,
    loginAsAdmin
} from "./helpers";

const ADMIN_USER = { email: "admin@local", password: "admin" };
const EMP1_USER = { email: "employee1@local", password: "employee1" };
const EMP2_USER = { email: "employee2@local", password: "employee2" };

let targetWorkspaceId: string;
let targetWorkspaceName: string;

test.describe.serial("Role Separation & Isolation", () => {
  test.beforeAll(async ({ browser }) => {
    // API-based setup context
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
        console.log("Starting Setup: Seeding users and workspaces via API...");
        
        // 1. Ensure Admins & Seed Users exist (Assuming pre-seeded or seed script ran)
        // Login as admin to perform API operations
        await loginAsAdmin(page);
        
        // 2. Ensure Employee 1 & 2 exist by UI/API check logic
        // Re-using ensureUserExists logic but adapted or relying on DEV_SEED
        await ensureUserExists(page, EMP1_USER);
        await ensureUserExists(page, EMP2_USER);

        // 3. Get Employee 2 ID
        const emp2Id = await adminGetUserIdByEmail(page, EMP2_USER.email);
        console.log(`Employee 2 ID: ${emp2Id}`);

        // 4. Create Private Workspace for Employee 2
        targetWorkspaceName = `Private Space Emp2 ${Date.now()}`;
        const ws = await adminCreateWorkspaceForUserId(page, emp2Id, targetWorkspaceName, "Secret stuff");
        targetWorkspaceId = ws.id;
        console.log(`Created Target Workspace: ${targetWorkspaceId} (${targetWorkspaceName})`);
        
    } catch (e) {
        console.error("Setup failed:", e);
        throw e;
    } finally {
        await page.close();
        await context.close();
    }
  });

  test.beforeEach(async ({ page }) => {
    await clearApiKeyStorage(page);
  });

  async function ensureUserExists(page: Page, user: {email: string, password: string}) {
      // Use API check first if possible, but fallback to UI flow if needed.
      // Since we are already logged in as admin (API session), we can use the UI admin console.
      // But we can also use listUsers API which is faster.
      const response = await page.request.get("/auth/users?limit=200");
      if (response.ok()) {
          const data = await response.json();
          const exists = data.users.some((u: any) => u.email === user.email);
          if (exists) {
              console.log(`User ${user.email} confirmed via API.`);
              return;
          }
      }
      
      // Fallback: Create via UI if not found (though DEV_SEED should have handled it)
      // Or use the create user API if we had one implemented.
      // For now, let's stick to the robust UI flow from before, updated.
      await page.goto("/admin/users");
      const userRow = page.locator(`[data-testid="admin-users-row"]`, { hasText: user.email });
      if (await userRow.count() > 0) return;

      console.log(`Seeding user ${user.email} via UI...`);
      await page.getByPlaceholder("empleado@ragcorp.com").fill(user.email);
      await page.getByPlaceholder("Min 8 caracteres").fill(user.password);
      await page.locator("select").first().selectOption("employee");
      
      const createPromise = page.waitForResponse(resp => 
        resp.url().includes("/users") && resp.request().method() === "POST"
      );
      await page.getByRole("button", { name: "Crear usuario" }).click();
      const res = await createPromise;
      if (!res.ok() && res.status() !== 409) {
          throw new Error(`Failed to create user ${user.email}`);
      }
      await page.reload(); // Refresh to be sure
  }

  test("Admin Redirection: Cannot access Employee Portal", async ({ page }) => {
    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    
    // Default landing should be Admin Console
    await expect(page).toHaveURL(/\/admin\/users/);

    // Navigating to Workspaces should be REDIRECTED back to Admin Console
    await page.goto("/workspaces");
    await expect(page).toHaveURL(/\/admin\/users/);
  });

  test("Employee Redirection: Cannot access Admin Console", async ({ page }) => {
    await login(page, EMP1_USER.email, EMP1_USER.password);

    // Default landing should be Workspaces
    await expect(page).toHaveURL(/\/workspaces/);
    
    // Try forcing URL to Admin Console
    await page.goto("/admin/users");
    // Should be redirected to /workspaces
    await expect(page).toHaveURL(/\/workspaces/);
  });

  test("Employee Isolation: Cannot see or access other employee's workspace", async ({ page }) => {
    // 1. Login as Employee 1
    await login(page, EMP1_USER.email, EMP1_USER.password);
    await expect(page).toHaveURL(/\/workspaces/);

    // 2. Verified via UI List: Target workspace should NOT be present
    const selector = page.getByTestId("workspace-selector");
    // Ideally we check specific options, or ensure the text doesn't contain the name
    // (Wait for selector to load first)
    await expect(selector).toBeVisible();
    const content = await selector.textContent();
    expect(content).not.toContain(targetWorkspaceName);
    
    const card = page.locator(`[data-testid^="workspace-card-"]`, { hasText: targetWorkspaceName });
    await expect(card).not.toBeVisible();

    // 3. API Assert: Direct access should be forbidden
    const apiRes = await page.request.get(`/api/workspaces/${targetWorkspaceId}/documents`);
    console.log(`API check for forbidden workspace: ${apiRes.status()}`);
    // Accept 403 Forbidden or 404 Not Found (security through obscurity)
    expect([403, 404]).toContain(apiRes.status());

    // 4. UI Assert: Direct navigation should show error
    await page.goto(`/workspaces/${targetWorkspaceId}/documents`);
    
    // We expect an error banner or similar indication
    // Or potentially a redirect to /workspaces if handled by useEffect
    // Let's check for the error banner defined in WorkspacesPage or AppShell
    /* 
      If AppShell fails to load workspace list containing this ID, 
      the selector won't select it, and the content might show "No hay workspaces visible" 
      or a generic error if the specific GET by ID fails.
    */
   
    // Let's wait a moment for the page logic to react
    await page.waitForTimeout(1000); 
    
    // Robust check: Either we are redirected back to root OR we see an error message
    const url = page.url();
    if (url.includes(`/workspaces/${targetWorkspaceId}`)) {
        // If we stayed on the page, ensures content is blocked
        // Check for specific error banner or empty/loading state that indicates failure
        // Assuming "Access denied" or generic error banner
        // Or if the backend returns 403, the frontend might show a toast
        
        // NOTE: The previous code mentioned "StatusBanner".
        // Let's assume a generic failure visible check.
        const errorMessage = page.locator("text=Error"); // loosely match error text
        // or check sources list is missing
        await expect(page.getByTestId("documents-list")).not.toBeVisible();
    } else {
        // Redirected is safe
        expect(url).not.toContain(targetWorkspaceId);
    }
  });
});
