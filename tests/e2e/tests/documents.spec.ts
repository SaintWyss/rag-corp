import { expect, test } from "@playwright/test";

test.describe("Documents flow", () => {
    const apiKey = process.env.TEST_API_KEY || "e2e-key";

    test.beforeEach(async ({ page }) => {
        await page.addInitScript((key) => {
            window.localStorage.setItem("ragcorp_api_key", key);
        }, apiKey);
        await page.goto("/documents");
    });

    test("ingest -> list -> detail -> delete", async ({ page }) => {
        const docTitle = `E2E Document ${Date.now()}`;
        const docText =
            "Este documento de prueba valida la ingesta y el CRUD desde la UI.";

        const titleInput = page.getByLabel("Titulo").first();
        const textInput = page.getByLabel("Texto").first();

        await titleInput.fill(docTitle);
        await textInput.fill(docText);

        await page.getByRole("button", { name: "Ingestar" }).click();
        await expect(page.getByText(/Documento listo/i)).toBeVisible();

        const listItem = page.getByRole("button", {
            name: new RegExp(docTitle),
        });
        await expect(listItem).toBeVisible();
        await listItem.click();

        await expect(page.getByText(docTitle)).toBeVisible();

        page.once("dialog", (dialog) => dialog.accept());
        await page.getByRole("button", { name: "Borrar documento" }).click();

        await expect(page.getByText("Documento eliminado.")).toBeVisible();
        await expect(
            page.getByRole("button", { name: new RegExp(docTitle) })
        ).toHaveCount(0);
    });
});
