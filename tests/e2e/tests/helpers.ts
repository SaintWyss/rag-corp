import { expect, type Page } from "@playwright/test";

function requireEnv(name: string): string {
    const value = process.env[name];  
    if (!value) {
        throw new Error(`Faltan env vars (${name}). Ejecuta: pnpm run e2e:run`);
    }
    return value;
}

export async function clearApiKeyStorage(page: Page) {
    await page.addInitScript(() => {
        window.sessionStorage.removeItem("ragcorp_api_key");
        window.localStorage.removeItem("ragcorp_api_key");
    });
}

export async function setSessionApiKey(page: Page, apiKey: string) {
    await page.addInitScript((key) => {
        window.sessionStorage.setItem("ragcorp_api_key", key);
    }, apiKey);
}

export async function loginAsAdmin(page: Page) {
    const email = requireEnv("E2E_ADMIN_EMAIL");
    const password = requireEnv("E2E_ADMIN_PASSWORD");
    const response = await page.request.post("/auth/login", {
        data: { email, password },
    });
    if (!response.ok()) {
        const body = await response.text();
        const status = response.status();
        let errorMsg = `Login failed (${status}): ${body || "empty response"}`;
        
        if (status >= 500) {
            errorMsg += "\n[HINT] Backend error. Check logs: docker compose logs rag-api --tail=200";
        }
        
        throw new Error(errorMsg);
    }
}

export async function adminListUsers(page: Page): Promise<any[]> {
    const response = await page.request.get("/auth/users?limit=200");
    if (!response.ok()) {
        throw new Error(`Failed to list users: ${response.status()} ${await response.text()}`);
    }
    const data = await response.json();
    return data.users || [];
}

export async function adminGetUserIdByEmail(page: Page, email: string): Promise<string> {
    const users = await adminListUsers(page);
    const user = users.find((u: any) => u.email === email);
    if (!user) {
        throw new Error(`User not found: ${email}`);
    }
    return user.id;
}

export async function adminCreateWorkspaceForUserId(
    page: Page, 
    ownerUserId: string, 
    name: string, 
    description?: string
): Promise<any> {
    const response = await page.request.post("/api/admin/workspaces", {
        data: {
            owner_user_id: ownerUserId,
            name,
            description
        }
    });

    if (!response.ok()) {
        const body = await response.text();
        throw new Error(`Failed to create workspace for user ${ownerUserId}: ${response.status()} ${body}`);
    }
    
    return await response.json();
}
export async function login(page: Page, email: string, password: string) {
  // 0) Limpieza fuerte
  await page.context().clearCookies();

  // 1) Login por API
  const res = await page.request.post("/auth/login", {
    data: { email, password },
  });

  if (!res.ok()) {
    const body = await res.text();
    throw new Error(`Login failed (${res.status()}): ${body || "empty response"}`);
  }

  const data = await res.json();
  const token: string | undefined = data?.access_token;
  const role: string | undefined = data?.user?.role;
  const expiresIn: number = typeof data?.expires_in === "number" ? data.expires_in : 1800;

  if (!token) {
    throw new Error(`Login response missing access_token. Body: ${JSON.stringify(data)}`);
  }

  // 2) Host para cookie (SIN puerto)
  // Usa E2E_BASE_URL si existe; sino localhost:3000.
  const base = process.env.E2E_BASE_URL || "http://localhost:3000";
  const host = new URL(base).hostname;
  const expires = Math.floor(Date.now() / 1000) + expiresIn;

  // 3) Set cookies usando domain+path (esto evita el error del todo)
  await page.context().addCookies([
    {
      name: "access_token",
      value: token,
      domain: host,
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      secure: false,
      expires,
    },
    // opcional: por compatibilidad si alguna parte busca este nombre
    {
      name: "rag_access_token",
      value: token,
      domain: host,
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      secure: false,
      expires,
    },
  ]);

  // 4) Verificación REAL: /auth/me tiene que dar 200 (si no, no hay sesión)
  const me = await page.request.get("/auth/me");
  if (!me.ok()) {
    throw new Error(`Session not established after cookie set. /auth/me -> ${me.status()} ${await me.text()}`);
  }

  // 5) Landing determinístico por rol
  const target = role === "admin" ? "/admin/users" : "/workspaces";
  await page.goto(target, { waitUntil: "domcontentloaded" });
  await expect(page).not.toHaveURL(/\/login/);
}



export async function createWorkspace(page: Page, name: string): Promise<string> {
    await page.goto("/workspaces");
    await expect(page.getByTestId("workspaces-page")).toBeVisible();
    await expect(page.getByTestId("workspaces-create-form")).toBeVisible();

    await page.getByTestId("workspaces-create-name").fill(name);
    const createResponse = page.waitForResponse((response) => {
        return (
            response.url().includes("/api/workspaces") &&
            response.request().method() === "POST"
        );
    });
    await page.getByTestId("workspaces-create-submit").click();
    const response = await createResponse;
    if (!response.ok()) {
        const body = await response.text();
        throw new Error(
            `Workspace create failed (${response.status()}): ${
                body || "empty response"
            }`
        );
    }

    await page.getByTestId("workspaces-refresh").click();

    const card = page.locator('[data-testid^="workspace-card-"]', {
        hasText: name,
    });
    await expect(card).toBeVisible({ timeout: 15000 });

    const testId = await card.getAttribute("data-testid");
    if (!testId) {
        throw new Error("Workspace card missing data-testid.");
    }
    return testId.replace("workspace-card-", "");
}

export async function uploadDocumentAndWaitReady(
    page: Page,
    workspaceId: string,
    title: string,
    filePath: string
): Promise<string> {
    await page.goto(`/workspaces/${workspaceId}/documents`);
    await expect(page.getByTestId("sources-workspace")).toContainText(
        workspaceId
    );

    await page.getByTestId("sources-title-input").fill(title);
    await page.getByTestId("sources-file-input").setInputFiles(filePath);
    await page.getByTestId("sources-upload-submit").click();

    const listItem = page.locator('[data-testid="source-list-item"]', {
        hasText: title,
    });
    await expect(listItem).toBeVisible();
    await listItem.click();

    const detail = page.getByTestId("source-detail");
    await expect(detail).toHaveAttribute("data-document-title", title);

    const status = page.getByTestId("source-detail-status");
    await expect(status).toBeVisible();

    for (let i = 0; i < 15; i += 1) {
        const text = (await status.textContent()) || "";
        if (text.includes("READY")) {
            break;
        }
        await page.getByTestId("sources-refresh").click();
        await page.waitForTimeout(2000);
    }

    await expect(status).toHaveText(/READY/);

    const docId = await detail.getAttribute("data-document-id");
    if (!docId) {
        throw new Error("Document detail missing data-document-id.");
    }
    return docId;
}

export async function adminEnsureUser(page: Page, user: {email: string, password: string}, role: 'admin' | 'employee' = 'employee') {
    // 1. Check API
    const response = await page.request.get("/auth/users?limit=200");
    if (response.ok()) {
        const data = await response.json();
        const exists = data.users.some((u: any) => u.email === user.email);
        if (exists) {
            console.log(`User ${user.email} exists (API check).`);
            return;
        }
    }
    
    // 2. Create via UI (Fallback robusto)
    // Asumimos que estamos logueados como admin.
    await page.goto("/admin/users");
    
    // Try waiting for hydration
    await expect(page.getByText("Usuarios del Sistema")).toBeVisible({ timeout: 5000 }).catch(() => {});

    try {
        await page.locator('[data-testid="admin-users-row"]').first().waitFor({ state: "visible", timeout: 2000 });
    } catch {
        // empty list OK
    }
    
    const userRow = page.locator(`[data-testid="admin-users-row"]`, { hasText: user.email });
    if (await userRow.count() > 0) return; // appeared

    console.log(`Creating user ${user.email}...`);
    await page.getByPlaceholder("empleado@ragcorp.com").fill(user.email);
    // password field placeholder check or generic
    await page.getByPlaceholder("Min 8 caracteres").fill(user.password);
    
    await page.locator("select").first().selectOption(role);
    
    const createPromise = page.waitForResponse(resp => 
        resp.url().includes("/users") && resp.request().method() === "POST"
    );

    await page.getByRole("button", { name: "Crear usuario" }).click();
    const res = await createPromise;
    
    if (!res.ok() && res.status() !== 409) {
        throw new Error(`Failed to create user ${user.email}: ${res.status()}`);
    }
    
    // Wait for row to appear to confirm UI update
    await expect(page.locator(`[data-testid="admin-users-row"]`, { hasText: user.email })).toBeVisible();
}
