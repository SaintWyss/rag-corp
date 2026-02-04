# frontend

Este directorio es el centro operativo del frontend. Este README esta pensado para personas sin experiencia previa en frontend, por lo que explica conceptos y estructura desde cero, con ejemplos y definiciones claras.

## Como leer este documento
1. Que es el frontend y como se conecta con el backend.
2. Mapa del directorio (archivos y carpetas).
3. Flujo de requests y responsabilidades.
4. Tecnologias: que son y por que se usan.
5. Guias practicas y troubleshooting.

---

## 1) Que es el frontend

El frontend es la parte del sistema que vive en el navegador. Su trabajo es:
- mostrar interfaces,
- navegar entre pantallas,
- validar acceso,
- pedir datos al backend,
- y transformar respuestas en UI.

En este proyecto el frontend es una app Next.js (React) con TypeScript. Se comunica con el backend por medio de rewrites (proxy interno) y valida sesiones con un middleware.

---

## 2) Mapa del directorio

### Archivos en la raiz
Estos archivos estan en la raiz porque Next.js y el tooling los buscan automaticamente.

| Archivo | Que es | Por que existe | Cuando tocarlo |
| :-- | :-- | :-- | :-- |
| `Dockerfile` | Config | Build y runtime (dev y prod) | Cambios de build, runtime o deps |
| `.dockerignore` | Config | Reduce contexto de build y evita secrets | Cuando aparecen archivos nuevos locales |
| `.gitignore` | Config | Evita commitear basura local | Cuando aparece nuevo cache |
| `middleware.ts` | Codigo | Guardia de rutas y validacion de sesion | Cambios de auth o rutas privadas |
| `next.config.mjs` | Config | Rewrites, output y settings | Cambios del contrato con backend |
| `postcss.config.mjs` | Config | Pipeline de CSS (Tailwind) | Cambios de tooling CSS |
| `eslint.config.mjs` | Config | Linting y reglas de arquitectura | Nuevas reglas o plugins |
| `tsconfig.json` | Config | Config de TypeScript | Cambios de paths/strictness |
| `next-env.d.ts` | Types | Bootstrap de tipos de Next.js | No editar manualmente |
| `package.json` | Config | Scripts y dependencias | Nuevos scripts o deps |
| `README.md` | Doc | Este documento | Cuando cambia la estructura |

### Carpetas principales
| Carpeta | Que hay adentro | Por que existe |
| :-- | :-- | :-- |
| `app/` | App Router (rutas, layouts) | Next usa el filesystem para routing |
| `src/` | Codigo de producto | Features, shared, app-shell, config y helpers |
| `public/` | Assets estaticos | Logos, imagenes, favicon |
| `tests/` | Tests | Unit e integration tests |
| `config/` | Configs de tooling | Jest y configs auxiliares |
| `docs/` | Docs internas | Arquitectura FE, runbooks |
| `scripts/` | Scripts | Codegen, checks |

---

## 3) Flujo de requests y responsabilidades

### Flujo tipico
1. El browser pide `/workspaces`.
2. Next.js resuelve la ruta en `app/`.
3. El `middleware.ts` valida la sesion llamando `/auth/me`.
4. Si la sesion es valida, renderiza la pagina.
5. Si no, redirige a `/login`.

### Rewrites (proxy interno)
- El frontend no llama al backend directo.
- Llama a `/api/*` o `/auth/*` en el mismo origen.
- Next.js reescribe a `RAG_BACKEND_URL`.
- Resultado: menos CORS y cookies httpOnly mas simples.

### Middleware (que hace exactamente)
- Verifica si hay cookie de sesion.
- Consulta `/auth/me` para validar usuario.
- Redirige a login si no hay sesion valida.
- Evita que un rol navegue por el portal incorrecto.

---

## 4) Tecnologias: que son y por que se usan

### Next.js
Framework para apps web con React. Aporta:
- Routing automatico por filesystem.
- Render server y client.
- Build optimizado y deploy simplificado.

#### Routing por filesystem
Ejemplo:
- `app/login/page.tsx` -> `/login`
- `app/workspaces/page.tsx` -> `/workspaces`

#### SSR, SSG, CSR (definiciones simples)
- SSR: el servidor genera HTML en cada request.
- SSG: el HTML se genera en build time.
- CSR: el browser renderiza con JS.

Next permite combinar segun necesidad.

### React
Biblioteca para construir UI con componentes. Un componente es una funcion que devuelve UI. Se combinan para construir pantallas.

### TypeScript
JavaScript con tipos. Sirve para:
- detectar errores antes de ejecutar,
- mejorar autocompletado,
- hacer refactors seguros.

### Tailwind CSS
Framework de estilos basado en clases utilitarias. Permite construir UI rapido sin escribir CSS manual por cada componente.

### PostCSS (pipeline)
PostCSS ejecuta un pipeline de transformaciones de CSS:
1. Lee el CSS fuente.
2. Ejecuta plugins (Tailwind).
3. Emite CSS listo para produccion.

### ESLint
Analiza el codigo y detecta errores o malas practicas sin ejecutar. En este repo tambien enforcea arquitectura (capas y limites).

### Jest + Testing Library
- Jest ejecuta los tests.
- Testing Library ayuda a testear UI como un usuario real.

### pnpm + workspaces
Administrador de paquetes mas eficiente que npm para monorepos. Reduce duplicados y acelera instalaciones.

### Docker
Empaqueta la app en una imagen reproducible. Hay target `dev` (hot reload) y `production` (standalone).

---

## 5) Arquitectura interna

### Reglas base
- `app/` es wiring (rutas y layouts). No poner logica de negocio.
- `src/` contiene el producto.
- `src/shared/` no depende de `src/features/`.
- Features no deben importarse entre si (solo via `index.ts`).

### Estructura dentro de `src/`
- `src/app-shell/`: providers, guards y layouts usados por `app/`.
- `src/features/<feature>/`: logica por feature (components/hooks/services/types).
- `src/shared/`: UI, api, lib y config reusables.
- `src/test/`: fixtures y helpers para tests.

---

## 6) Testing

```bash
pnpm -C apps/frontend test
```

Config:
- `config/jest.config.js`
- `config/jest.setup.ts`

Estructura:
- `tests/unit/**` para unit tests
- `tests/integration/**` para integration tests
- `src/test/**` para fixtures y helpers

---

## 7) Docker

Dev:
```bash
docker build --target dev -t rag-frontend-dev .
```

Prod:
```bash
docker compose --profile ui up -d --build
```

---

## 8) Variables de entorno
- `RAG_BACKEND_URL`: backend base para rewrites/middleware.
- `AUTH_ME_TIMEOUT_MS`: timeout de `/auth/me`.
- `JWT_COOKIE_NAME`: nombre de cookie de auth.
- `JWT_COOKIE_DOMAIN`: opcional si se setea Domain.

---

## 9) Buenas practicas
- Pensar siempre en capas: wiring vs producto.
- Componentes reusables en `src/shared/ui/`.
- Logica de feature dentro de su carpeta (sin depender de otros features).
- Respetar el contrato `/api` y `/auth`.

---

## 10) Troubleshooting rapido

- **No encuentra alias `@/`**
- Causa: archivo fuera de `src/` o alias mal configurado.
- Solucion: mover a `src/` o revisar `tsconfig.json`.

- **/api falla**
- Causa: backend caido o `RAG_BACKEND_URL` incorrecto.
- Solucion: revisar `.env` o `compose.yaml`.

- **Siempre redirige a /login**
- Causa: cookie invalida o timeout de `/auth/me`.
- Solucion: revisar `JWT_COOKIE_NAME` y `AUTH_ME_TIMEOUT_MS`.

---

## Recursos recomendados
```text
Next.js App Router: https://nextjs.org/docs/app
React Docs: https://react.dev/learn
TypeScript Handbook: https://www.typescriptlang.org/docs/
Tailwind CSS: https://tailwindcss.com/docs
PostCSS: https://postcss.org/
Testing Library: https://testing-library.com/docs/
Jest: https://jestjs.io/docs/getting-started
ESLint Flat Config: https://eslint.org/docs/latest/use/configure/configuration-files
pnpm Workspaces: https://pnpm.io/workspaces
Docker: https://docs.docker.com/get-started/
```

---

## Ver tambien
- `./docs/README.md`
- `./config/jest.config.js`
- `./middleware.ts`
- `./next.config.mjs`
