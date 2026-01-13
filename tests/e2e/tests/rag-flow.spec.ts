import { expect, test } from "@playwright/test";

/**
 * E2E Tests: RAG Flow
 *
 * These tests verify the complete RAG workflow:
 * 1. Document ingestion
 * 2. Query/search
 * 3. Answer generation
 */

test.describe("RAG Flow", () => {
    const apiKey = process.env.TEST_API_KEY || "test-key";

    test.describe("Document Ingestion", () => {
        test("can ingest a document via API", async ({ request }) => {
            const response = await request.post("http://localhost:8000/v1/ingest/text", {
                headers: {
                    "X-API-Key": apiKey,
                    "Content-Type": "application/json",
                },
                data: {
                    title: "E2E Test Document",
                    text: "This is a test document for end-to-end testing. It contains information about software testing practices and automation.",
                    source: "e2e-test",
                    metadata: { test: true },
                },
            });

            // May fail if auth is required and key is invalid
            if (response.status() === 401) {
                test.skip();
                return;
            }

            expect(response.ok()).toBeTruthy();
            const body = await response.json();
            expect(body.document_id).toBeDefined();
            expect(body.chunks).toBeGreaterThan(0);
        });
    });

    test.describe("Query/Search", () => {
        test("can search for documents via API", async ({ request }) => {
            const response = await request.post("http://localhost:8000/v1/query", {
                headers: {
                    "X-API-Key": apiKey,
                    "Content-Type": "application/json",
                },
                data: {
                    query: "software testing",
                    top_k: 3,
                },
            });

            // May fail if auth is required and key is invalid
            if (response.status() === 401) {
                test.skip();
                return;
            }

            expect(response.ok()).toBeTruthy();
            const body = await response.json();
            expect(body.matches).toBeDefined();
            expect(Array.isArray(body.matches)).toBe(true);
        });
    });

    test.describe("Answer Generation", () => {
        test("can get an answer via API", async ({ request }) => {
            const response = await request.post("http://localhost:8000/v1/ask", {
                headers: {
                    "X-API-Key": apiKey,
                    "Content-Type": "application/json",
                },
                data: {
                    query: "What is software testing?",
                    top_k: 3,
                },
            });

            // May fail if auth is required and key is invalid
            if (response.status() === 401) {
                test.skip();
                return;
            }

            // May fail if Google API key is not configured
            if (response.status() === 503) {
                test.skip();
                return;
            }

            expect(response.ok()).toBeTruthy();
            const body = await response.json();
            expect(body.answer).toBeDefined();
            expect(body.sources).toBeDefined();
        });
    });
});
