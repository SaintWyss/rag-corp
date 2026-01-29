import fs from "fs";
import path from "path";
import { expect, type Page } from "@playwright/test";

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Faltan env vars (${name}). Ejecuta: pnpm run e2e:run`);
  }
  return value;
}

export function hasAdminCredentials(): boolean {
  return Boolean(process.env.E2E_ADMIN_EMAIL && process.env.E2E_ADMIN_PASSWORD);
}

// Origen único y validado para cookies
function getOrigin(): string {
  const raw =
    process.env.E2E_BASE_URL ||
    process.env.PLAYWRIGHT_BASE_URL ||
    "http://localhost:3000";

  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(
      `E2E_BASE_URL inválida: "${raw}". Debe ser tipo "http://localhost:3000"`
    );
  }
  return url.origin; // "http://localhost:3000"
}

function cookieNamePrimary(): string {
  return (
    process.env.JWT_COOKIE_NAME ||
    process.env.NEXT_PUBLIC_JWT_COOKIE_NAME ||
    "rag_access_token"
  );
}

async function setAuthCookie(
  page: Page,
  token: string,
  expiresInSeconds = 1800
) {
  const origin = getOrigin();
  const u = new URL(origin);

  const domain = u.hostname; // localhost / tu host real
  const secure = u.protocol === "https:"; // http localhost => false
  const expires = Math.floor(Date.now() / 1000) + expiresInSeconds;

  // Limpieza dura
  await page.context().clearCookies();

  const primary = cookieNamePrimary();

  // Seteamos compat: primary + access_token + rag_access_token
  const names = Array.from(new Set([primary, "access_token", "rag_access_token"]));

  /**
   * IMPORTANTÍSIMO:
   * Usar domain+path (path="/") para que el cookie aplique a /admin y /workspaces.
   * Con `url:` a veces termina scoping raro y te manda a /login en /admin.
   */
  await page.context().addCookies(
    names.map((name) => ({
      name,
      value: token,
      domain,
      path: "/", // ✅ aplica a TODO el sitio
      httpOnly: true,
      secure, // ✅ false en http://localhost
      sameSite: "Lax",
      expires,
    }))
  );

  // Verificación REAL: cookie aplica a /workspaces Y a /admin/users
  const adminUrl = `${origin}/admin/users`;
  const workspacesUrl = `${origin}/workspaces`;

  await expect
    .poll(
      async () => {
        const cAdmin = await page.context().cookies(adminUrl);
        const cWs = await page.context().cookies(workspacesUrl);

        const okAdmin = cAdmin.some(
          (c) => names.includes(c.name) && c.path === "/" && c.domain.includes(domain)
        );
        const okWs = cWs.some(
          (c) => names.includes(c.name) && c.path === "/" && c.domain.includes(domain)
        );

        return okAdmin && okWs;
      },
      {
        timeout: 10_000,
        message:
          "Auth cookie no quedó seteada para /admin y /workspaces (path=/).",
      }
    )
    .toBeTruthy();
}

/**
 * Login por API -> obtenemos token -> seteamos cookie en el browser context.
 * Esto evita flakes de UI login y asegura que page.goto() NO caiga en /login.
 */
async function apiLogin(page: Page, email: string, password: string) {
  const res = await page.request.post("/auth/login", {
    data: { email, password },
  });

  if (!res.ok()) {
    const body = await res.text();
    const status = res.status();
    let errorMsg = `Login failed (${status}): ${body || "empty response"}`;
    if (status >= 500) {
      errorMsg +=
        "\n[HINT] Backend error. Check logs: docker compose logs rag-api --tail=200";
    }
    throw new Error(errorMsg);
  }

  const data: any = await res.json();
  const token = data?.access_token;
  const expiresIn =
    typeof data?.expires_in === "number" ? data.expires_in : 1800;

  if (!token) {
    throw new Error(
      `Login response missing access_token. Body: ${JSON.stringify(data)}`
    );
  }

  await setAuthCookie(page, token, expiresIn);

  // Fuente de verdad del rol: /auth/me (ya usando cookie real del browser)
  const me = await page.request.get("/auth/me");
  if (!me.ok()) {
    throw new Error(
      `Auth sanity failed after login: ${me.status()} ${await me.text()}`
    );
  }

  const user: any = await me.json();
  const role = user?.role as "admin" | "employee" | undefined;

  if (!role) {
    throw new Error(
      `Auth /auth/me missing role. Body: ${JSON.stringify(user)}`
    );
  }

  return { role, token, expiresIn };
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

/**
 * Login ADMIN para setup (API + cookie browser).
 */
export async function loginAsAdmin(page: Page) {
  const email = requireEnv("E2E_ADMIN_EMAIL");
  const password = requireEnv("E2E_ADMIN_PASSWORD");

  const { role } = await apiLogin(page, email, password);
  if (role !== "admin") {
    throw new Error(`E2E_ADMIN_EMAIL no es admin. role=${role} email=${email}`);
  }
}

/**
 * Login genérico (API -> cookie -> landing determinístico).
 */
export async function login(page: Page, email: string, password: string) {
  const { role } = await apiLogin(page, email, password);

  const landing = role === "admin" ? "/admin/users" : "/workspaces";
  await page.goto(landing, { waitUntil: "domcontentloaded" });

  await expect(
    page,
    "Si termina en /login acá, NO hay sesión en el browser"
  ).not.toHaveURL(/\/login/, { timeout: 15_000 });
}

async function getAdminToken(page: Page): Promise<string> {
  const email = requireEnv("E2E_ADMIN_EMAIL");
  const password = requireEnv("E2E_ADMIN_PASSWORD");
  const { role, token } = await apiLogin(page, email, password);
  if (role !== "admin") {
    throw new Error(`E2E_ADMIN_EMAIL no es admin. role=${role} email=${email}`);
  }
  return token;
}

export async function createWorkspace(page: Page, name: string) {
  const token = await getAdminToken(page);
  const response = await page.request.post("/api/workspaces", {
    data: { name },
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to create workspace: ${response.status()} ${body}`
    );
  }

  const data: any = await response.json();
  if (!data?.id) {
    throw new Error(`Workspace create response missing id: ${JSON.stringify(data)}`);
  }
  return data.id as string;
}

export async function uploadDocumentAndWaitReady(
  page: Page,
  workspaceId: string,
  title: string,
  filePath: string
): Promise<string> {
  const fileBuffer = fs.readFileSync(filePath);
  const filename = path.basename(filePath);

  const upload = await page.request.post(
    `/api/workspaces/${workspaceId}/documents/upload`,
    {
      multipart: {
        title,
        file: {
          name: filename,
          mimeType: "application/pdf",
          buffer: fileBuffer,
        },
      },
    }
  );

  if (!upload.ok()) {
    const body = await upload.text();
    throw new Error(`Upload failed: ${upload.status()} ${body}`);
  }

  const uploadData: any = await upload.json();
  const documentId = uploadData?.id;
  if (!documentId) {
    throw new Error(`Upload response missing id: ${JSON.stringify(uploadData)}`);
  }

  await expect
    .poll(
      async () => {
        const res = await page.request.get(
          `/api/workspaces/${workspaceId}/documents/${documentId}`
        );
        if (!res.ok()) {
          return { ok: false, status: res.status(), state: "ERROR" };
        }
        const doc = (await res.json()) as { status?: string; error_message?: string };
        return { ok: true, status: res.status(), state: doc.status ?? "UNKNOWN" };
      },
      { timeout: 60_000, message: "Document did not reach READY in time." }
    )
    .toMatchObject({ ok: true, state: "READY" });

  return documentId as string;
}

export async function adminListUsers(page: Page): Promise<any[]> {
  const response = await page.request.get("/auth/users?limit=200");
  if (!response.ok()) {
    throw new Error(
      `Failed to list users: ${response.status()} ${await response.text()}`
    );
  }
  const data = await response.json();
  return data.users || [];
}

export async function adminGetUserIdByEmail(
  page: Page,
  email: string
): Promise<string> {
  const users = await adminListUsers(page);
  const user = users.find((u: any) => u.email === email);
  if (!user) throw new Error(`User not found: ${email}`);
  return user.id;
}

/**
 * Ensure user via ADMIN API (evita UI flake).
 * Si ya existe -> OK.
 */
export async function adminEnsureUser(
  page: Page,
  user: { email: string; password: string },
  role: "admin" | "employee" = "employee"
) {
  const users = await adminListUsers(page);
  const exists = users.some((u: any) => u.email === user.email);
  if (exists) return;

  const res = await page.request.post("/auth/users", {
    data: { email: user.email, password: user.password, role },
  });

  if (!res.ok() && res.status() !== 409) {
    throw new Error(
      `Failed to create user ${user.email}: ${res.status()} ${await res.text()}`
    );
  }
}

export async function adminCreateWorkspaceForUserId(
  page: Page,
  ownerUserId: string,
  name: string,
  description?: string
): Promise<any> {
  const response = await page.request.post("/api/admin/workspaces", {
    data: { owner_user_id: ownerUserId, name, description },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to create workspace for user ${ownerUserId}: ${response.status()} ${body}`
    );
  }

  return await response.json();
}
