import { defineConfig } from "orval";

export default defineConfig({
  rag: {
    input: "./openapi.json",
    output: {
      mode: "single",
      target: "./src/generated.ts",
      client: "fetch",
      clean: true
    }
  }
});
