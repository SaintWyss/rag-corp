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

export async function login(page: Page, email: string, password: string) {
    await page.goto("/login");
    await page.getByPlaceholder("name@example.com").fill(email);
    await page.getByPlaceholder("••••••••").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    // Wait for login to complete (redirect away from login)
    await page.waitForURL((url) => !url.pathname.includes("/login"));
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
