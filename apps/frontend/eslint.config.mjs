/**
===============================================================================
TARJETA CRC — apps/frontend/eslint.config.mjs (Linting + Arquitectura)
===============================================================================

Responsabilidades:
  - Definir configuración ESLint (Flat Config) para Next.js + TypeScript.
  - Mantener reglas coherentes con Clean Code (evitar footguns comunes).
  - Enforcear límites de arquitectura mínimos (shared no depende de features).
  - Ajustar reglas para tests (no frenar DX, pero mantener calidad).

Colaboradores:
  - ESLint (flat config)
  - eslint-config-next (core-web-vitals + typescript)
  - TypeScript / Next.js app router

Patrones aplicados:
  - “Policy as code” (reglas como contrato de equipo)
  - Layered architecture enforcement (mínimo viable sin plugins extra)

Errores y respuestas:
  - Si una importación viola capas, ESLint falla el check.
  - Si un archivo cae en ignores, ESLint no lo evalúa.

Invariantes:
  - `src/shared/**` nunca importa desde `src/features/**`.
  - Tests pueden ser más permisivos sin comprometer reglas del producto.
===============================================================================
*/

import boundaries from "eslint-plugin-boundaries";
import importPlugin from "eslint-plugin-import";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import unusedImports from "eslint-plugin-unused-imports";
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Convención de paths:
 * - En este repo, `@/` apunta a `src/` (por tsconfig paths).
 * - `app/` queda fuera de `@/` (App Router). Evitamos que `src/` dependa de `app/`.
 *
 * Nota:
 * - En Flat Config, los “overrides” se modelan como objetos con `files`.
 */

const JS_TS_FILES = ["**/*.{js,jsx,ts,tsx,mjs,cjs}"];
const SRC_APP_FILES = ["src/**/*.{js,jsx,ts,tsx}", "app/**/*.{js,jsx,ts,tsx}"];
const CONFIG_DIR = path.dirname(fileURLToPath(import.meta.url));

const BOUNDARIES_ELEMENTS = [
  // App Router (wiring)
  { type: "app", pattern: "app/*", capture: ["segment"] },

  // Shared (infra / primitives)
  { type: "shared", pattern: "src/shared/*", capture: ["segment"] },

  // Feature entrypoint (public API)
  {
    type: "feature-entry",
    pattern: "index.{ts,tsx}",
    basePattern: "src/features/*",
    baseCapture: ["feature"],
    mode: "file",
  },

  // Features (bounded by feature name)
  { type: "features", pattern: "src/features/*", capture: ["feature"] },

  // Other src slices (optional, but helps boundaries)
  { type: "components", pattern: "src/components/*", capture: ["segment"] },
  { type: "hooks", pattern: "src/hooks/*", capture: ["segment"] },
  { type: "services", pattern: "src/services/*", capture: ["segment"] },
  { type: "utils", pattern: "src/utils/*", capture: ["segment"] },

  // Root lib (root /lib)
  { type: "root-lib", pattern: "lib/*", capture: ["segment"] },
];

export default defineConfig([
  // ---------------------------------------------------------------------------
  // Base: Next.js recomendado (Core Web Vitals + TypeScript)
  // ---------------------------------------------------------------------------
  ...nextVitals,
  ...nextTs,

  // ---------------------------------------------------------------------------
  // Global ignores (repo hygiene)
  // - Evita ruido y acelera lint.
  // - Incluye ignores típicos + específicos del repo.
  // ---------------------------------------------------------------------------
  globalIgnores([
    // Default Next ignores / outputs:
    ".next/**",
    "out/**",
    "build/**",
    "dist/**",
    "next-env.d.ts",

    // Monorepo / tooling:
    "node_modules/**",
    ".turbo/**",
    ".swc/**",

    // Testing artifacts:
    "coverage/**",
    "playwright-report/**",
    "test-results/**",

    // Temp / logs:
    "*.log",
    "*.tmp",
    "*.bak",
  ]),

  // ---------------------------------------------------------------------------
  // Reglas generales de calidad (no type-aware: rápidas y útiles)
  // ---------------------------------------------------------------------------
  {
    files: JS_TS_FILES,
    plugins: {
      boundaries,
      import: importPlugin,
      "simple-import-sort": simpleImportSort,
      "unused-imports": unusedImports,
    },
    settings: {
      "boundaries/elements": BOUNDARIES_ELEMENTS,
    },
    rules: {
      // Anti-footguns
      "no-debugger": "error",
      "no-duplicate-imports": "error",
      "no-constant-condition": ["error", { checkLoops: false }],
      "prefer-const": "error",

      // Igualdad estricta (evita bugs silenciosos)
      eqeqeq: ["error", "always", { null: "ignore" }],

      // Console: permitido (warn) porque hay server-side (middleware) y debugging real.
      // Si querés más estricto: lo movemos a "error" y hacemos override por entorno.
      "no-console": ["warn", { allow: ["warn", "error"] }],

      // Orden de imports/exports
      "simple-import-sort/imports": "error",
      "simple-import-sort/exports": "error",

      // Imports no usados / vars no usadas (con _ permitido)
      "unused-imports/no-unused-imports": "error",
      "unused-imports/no-unused-vars": [
        "warn",
        {
          vars: "all",
          varsIgnorePattern: "^_",
          args: "after-used",
          argsIgnorePattern: "^_",
        },
      ],
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "off",

      // Import hygiene
      "import/no-cycle": "error",
      "import/no-extraneous-dependencies": [
        "error",
        {
          devDependencies: false,
          optionalDependencies: false,
          peerDependencies: false,
          packageDir: [CONFIG_DIR],
        },
      ],
    },
  },

  // ---------------------------------------------------------------------------
  // Arquitectura: enforced via boundaries
  // ---------------------------------------------------------------------------
  {
    files: SRC_APP_FILES,
    plugins: { boundaries },
    settings: {
      "boundaries/elements": BOUNDARIES_ELEMENTS,
    },
    rules: {
      "boundaries/element-types": [
        "error",
        {
          default: "allow",
          rules: [
            // src/shared no depende de features (ni siquiera via entrypoint)
            { from: ["shared"], disallow: ["features", "feature-entry"] },

            // src/** no depende de app/** (wiring)
            {
              from: ["shared", "features", "components", "hooks", "services", "utils"],
              disallow: ["app"],
            },

            // features no depende de otras features (excepto entrypoint si aplica)
            {
              from: ["features"],
              disallow: [["features", { feature: "!${from.feature}" }]],
            },
          ],
        },
      ],
    },
  },

  // ---------------------------------------------------------------------------
  // Configs: permitir CJS/require y devDependencies
  // ---------------------------------------------------------------------------
  {
    files: ["eslint.config.mjs", "next.config.mjs", "config/**/*.{js,cjs,mjs,ts}"],
    rules: {
      "@typescript-eslint/no-require-imports": "off",
      "import/no-extraneous-dependencies": [
        "error",
        {
          devDependencies: true,
          optionalDependencies: false,
          peerDependencies: false,
          packageDir: [CONFIG_DIR],
        },
      ],
    },
  },

  // ---------------------------------------------------------------------------
  // Tests: más permisivo para DX, sin romper reglas del producto.
  // ---------------------------------------------------------------------------
  {
    files: [
      "__tests__/**/*.{ts,tsx,js,jsx}",
      "**/*.test.{ts,tsx,js,jsx}",
      "**/*.spec.{ts,tsx,js,jsx}",
    ],
    rules: {
      "no-console": "off",
      eqeqeq: "off",
      "import/no-extraneous-dependencies": [
        "error",
        {
          devDependencies: true,
          optionalDependencies: false,
          peerDependencies: false,
          packageDir: [CONFIG_DIR],
        },
      ],
    },
  },
]);
