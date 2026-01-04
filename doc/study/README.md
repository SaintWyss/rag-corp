# Guion de estudio (solo preguntas)

Indice
1. [Quickstart & ejecucion local (compose, env vars, puertos)](#quickstart-ejecucion-local)
2. [Mapa del repo (arbol por carpetas importantes)](#mapa-del-repo)
3. [Flujo principal "Ask" end-to-end (Frontend -> Backend -> DB -> LLM -> respuesta)](#flujo-ask-end-to-end)
4. [Flujo "Ingest" (si existe) end-to-end](#flujo-ingest-end-to-end)
5. [Backend: entrypoints y routing (main.py, routes, versioning)](#backend-entrypoints-y-routing)
6. [Backend: DI/container y wiring](#backend-di-container-y-wiring)
7. [Backend: domain/application/infrastructure (responsabilidades + dependencias)](#backend-domain-application-infrastructure)
8. [Backend: Postgres/pgvector + schema (init.sql, repos, queries)](#backend-postgres-pgvector-schema)
9. [Backend: prompts/context builder + limites + seguridad basica contra prompt injection](#backend-prompts-context-builder-seguridad)
10. [Backend: auth, scopes, rate limit, metrics, logging, middlewares](#backend-auth-scopes-rate-limit-metrics-logging-middleware)
11. [Frontend: estructura App Router, hooks, components](#frontend-app-router-hooks-components)
12. [Frontend: API rewrites/config/env vars + manejo de errores](#frontend-api-rewrites-config-env-errores)
13. [Contracts: OpenAPI export, Orval, @contracts, regeneracion](#contracts-openapi-orval-regeneracion)
14. [CI: workflows (jobs, comandos exactos, por que falla cada uno)](#ci-workflows)
15. [Dependabot y reglas de mantenimiento](#dependabot-mantenimiento)
16. [Docs del repo: que esta actualizado vs que esta drifted (lista de checks/preguntas)](#docs-actualizado-vs-drifted)
17. ["Cambios tipicos" y como no romper nada (playbook de preguntas)](#cambios-tipicos-playbook)
18. [Preguntas de auditoria](#preguntas-de-auditoria)
19. [Preguntas para refactors futuros (no ejecutar)](#preguntas-refactors-futuros-no-ejecutar)

1. <a id="quickstart-ejecucion-local"></a>Quickstart & ejecucion local (compose, env vars, puertos)
   - Objetivo: Ejecutar local y validar puertos/servicios basicos.
   - Que necesito tener abierto:
     - `README.md`
     - `doc/runbook/local-dev.md`
     - `.env.example`
     - `compose.yaml`
     - `compose.prod.yaml`
     - `compose.observability.yaml`
     - `package.json`
   - Preguntas:
     1. Que pasos exactos de quickstart aparecen en `README.md` y `doc/runbook/local-dev.md`?
     2. Que servicios define `compose.yaml` y que puertos publica cada uno?
     3. Que variables requeridas aparecen en `.env.example` para iniciar el backend?
     4. Que comandos de `package.json` se usan para `docker:up`, `docker:down`, `dev` y contracts?
     5. Que servicios y puertos agrega `compose.observability.yaml`?
     6. Que endpoints de salud existen en `backend/app/main.py` y como se prueban en los docs?
     7. `compose.prod.yaml` usa `/health` en su healthcheck; existe esa ruta en `backend/app/main.py`? Si no, TODO/Planned.
   - Checkpoint:
     - Puedo levantar `db` y `rag-api` con `docker compose`.
     - Se que puerto usa cada servicio local.
     - Se que endpoints probar para salud y metrics.

2. <a id="mapa-del-repo"></a>Mapa del repo (arbol por carpetas importantes)
   - Objetivo: Ubicar las piezas principales del monorepo.
   - Que necesito tener abierto:
     - `README.md`
     - `doc/README.md`
   - Preguntas:
     1. Que carpetas top-level aparecen en `README.md` y coinciden con el arbol real?
     2. Donde viven `backend/`, `frontend/`, `shared/`, `infra/` y `doc/`?
     3. Donde esta el entrypoint del backend (`backend/app/main.py`)?
     4. Donde esta el App Router del frontend (`frontend/app`)?
     5. Donde viven los contratos y el OpenAPI (`shared/contracts/openapi.json`)?
     6. Que docs fuente lista `doc/README.md`?
     7. Donde estan los tests de backend y frontend?
   - Checkpoint:
     - Puedo ubicar backend, frontend, shared y infra sin buscar.
     - Se donde estan los contratos y la doc fuente.
     - Se donde viven los tests.

3. <a id="flujo-ask-end-to-end"></a>Flujo principal "Ask" end-to-end (Frontend -> Backend -> DB -> LLM -> respuesta)
   - Objetivo: Trazar el camino completo del request de ask.
   - Que necesito tener abierto:
     - `frontend/app/page.tsx`
     - `frontend/app/hooks/useRagAsk.ts`
     - `shared/contracts/openapi.json`
     - `backend/app/routes.py`
     - `backend/app/application/use_cases/answer_query.py`
     - `backend/app/application/context_builder.py`
     - `backend/app/infrastructure/repositories/postgres_document_repo.py`
     - `backend/app/infrastructure/services/google_llm_service.py`
   - Preguntas:
     1. Que hook dispara el submit en `frontend/app/page.tsx` y que props recibe?
     2. Que funcion de `@contracts` se llama en `useRagAsk.ts` y con que payload?
     3. Que ruta y metodo aparecen en `shared/contracts/openapi.json` para ask?
     4. Que handler en `backend/app/routes.py` atiende `/v1/ask` y que response model usa?
     5. En `AnswerQueryUseCase`, en que orden se hacen embed, retrieve, context y llm?
     6. Como `ContextBuilder` arma y limita el contexto (delimiters y max chars)?
     7. Que query usa `find_similar_chunks` y como calcula el score?
     8. Como `GoogleLLMService` carga el prompt y genera la respuesta?
   - Checkpoint:
     - Puedo seguir el flujo de una pregunta desde UI hasta DB y LLM.
     - Se donde se define el contrato y el response final.
     - Se donde se arma el contexto y el prompt.

4. <a id="flujo-ingest-end-to-end"></a>Flujo "Ingest" (si existe) end-to-end
   - Objetivo: Entender como entra un documento al sistema.
   - Que necesito tener abierto:
     - `frontend/app`
     - `backend/app/routes.py`
     - `backend/app/application/use_cases/ingest_document.py`
     - `backend/app/infrastructure/text/chunker.py`
     - `backend/app/infrastructure/services/google_embedding_service.py`
     - `backend/app/infrastructure/repositories/postgres_document_repo.py`
     - `infra/postgres/init.sql`
   - Preguntas:
     1. Existe UI o hook de ingest en `frontend/app`? Si no, TODO/Planned: que falta?
     2. Que endpoints de ingest existen en `backend/app/routes.py` y que modelos usan?
     3. Que datos recibe `IngestDocumentUseCase` y que devuelve?
     4. Que estrategia de chunking usa `chunker.py` y que defaults se inyectan desde `container.py`?
     5. Que modelo y `task_type` usa `GoogleEmbeddingService` para `embed_batch`?
     6. Que operaciones atomicas hace `save_document_with_chunks`?
     7. Que columnas y tablas reciben documentos y chunks en `infra/postgres/init.sql`?
   - Checkpoint:
     - Puedo ubicar endpoints y use case de ingest.
     - Se donde se chunkear y embebear texto.
     - Se donde se persiste en Postgres.

5. <a id="backend-entrypoints-y-routing"></a>Backend: entrypoints y routing (main.py, routes, versioning)
   - Objetivo: Ubicar entrypoints, prefijos y rutas.
   - Que necesito tener abierto:
     - `backend/app/main.py`
     - `backend/app/routes.py`
     - `backend/app/versioning.py`
   - Preguntas:
     1. Donde se crea la app FastAPI y que metadata se define?
     2. Que middlewares se agregan en `main.py` y en que orden?
     3. Que router se monta bajo `/v1` y que helper agrega `/api/v1`?
     4. Que endpoints de soporte expone `main.py`?
     5. Que tags usan los endpoints en `routes.py`?
     6. Hay rutas reales en `/api/v2` segun `versioning.py`? Si no, TODO/Planned.
     7. Donde se definen los modelos de request/response de FastAPI?
   - Checkpoint:
     - Se que prefijos y rutas expone la API.
     - Puedo ubicar el entrypoint y el router principal.
     - Entiendo el estado de versionado v1/v2.

6. <a id="backend-di-container-y-wiring"></a>Backend: DI/container y wiring
   - Objetivo: Entender como se crean e inyectan dependencias.
   - Que necesito tener abierto:
     - `backend/app/container.py`
     - `backend/app/routes.py`
     - `backend/app/config.py`
   - Preguntas:
     1. Que factories singleton existen en `container.py` y que implementaciones devuelven?
     2. Que dependencias reciben `AnswerQueryUseCase`, `IngestDocumentUseCase` y `SearchChunksUseCase`?
     3. Donde se leen `chunk_size` y `chunk_overlap` para el chunker?
     4. Que providers se usan en `routes.py` via `Depends`?
     5. Que cosas estan cacheadas con `lru_cache` y por que?
     6. Hay algun provider para reemplazar implementaciones en tests (buscar en `backend/tests`)?
   - Checkpoint:
     - Se de donde salen repos, servicios y chunker.
     - Puedo mapear cada use case a sus dependencias.
     - Se como se enchufa DI en las rutas.

7. <a id="backend-domain-application-infrastructure"></a>Backend: domain/application/infrastructure (responsabilidades + dependencias)
   - Objetivo: Confirmar la separacion de capas y responsabilidades.
   - Que necesito tener abierto:
     - `backend/app/domain/entities.py`
     - `backend/app/domain/repositories.py`
     - `backend/app/domain/services.py`
     - `backend/app/application/use_cases`
     - `backend/app/application/context_builder.py`
     - `backend/app/infrastructure`
     - `backend/app/container.py`
   - Preguntas:
     1. Que entidades define `domain/entities.py` y que campos clave tienen?
     2. Que interfaces define `domain/repositories.py` y `domain/services.py`?
     3. Que casos de uso existen en `application/use_cases`?
     4. Donde vive `ContextBuilder` y quien lo llama?
     5. Que clases concretas de infraestructura implementan repos y servicios?
     6. Hay modulos en `infrastructure/` no cableados en `container.py` (ej `semantic_chunker.py`, `cache.py`)? Si si, TODO/Planned.
     7. Hay imports que rompen la direccion de dependencias entre capas?
   - Checkpoint:
     - Puedo explicar quien depende de quien en las capas.
     - Se donde estan entidades, interfaces y casos de uso.
     - Se que infraestructura esta cableada y cual no.

8. <a id="backend-postgres-pgvector-schema"></a>Backend: Postgres/pgvector + schema (init.sql, repos, queries)
   - Objetivo: Ver como se persiste y consulta con pgvector.
   - Que necesito tener abierto:
     - `infra/postgres/init.sql`
     - `backend/app/infrastructure/repositories/postgres_document_repo.py`
     - `backend/app/infrastructure/db/pool.py`
     - `backend/app/config.py`
     - `.env.example`
   - Preguntas:
     1. Que tablas y columnas crea `infra/postgres/init.sql`?
     2. Existe columna `deleted_at` en `documents` para `soft_delete_document`? Si no, TODO/Planned.
     3. Que dimension de embedding se usa y donde se valida?
     4. Que index de vector se crea y con que parametros?
     5. Que query exacta usa `find_similar_chunks` y como calcula el score?
     6. Donde se configura el pool (min/max) y el statement timeout?
     7. Que `DATABASE_URL` se recomienda en `.env.example` para local?
   - Checkpoint:
     - Se que tablas e indices existen.
     - Se como se hace la busqueda vectorial.
     - Se donde se configura el pool y timeouts.

9. <a id="backend-prompts-context-builder-seguridad"></a>Backend: prompts/context builder + limites + seguridad basica contra prompt injection
   - Objetivo: Ver como se arma el prompt y el contexto.
   - Que necesito tener abierto:
     - `backend/app/prompts/v1_answer_es.md`
     - `backend/app/infrastructure/prompts/loader.py`
     - `backend/app/application/context_builder.py`
     - `backend/app/config.py`
     - `.env.example`
   - Preguntas:
     1. Que placeholders usa `v1_answer_es.md` y donde se insertan?
     2. Donde se definen `PROMPT_VERSION` y `MAX_CONTEXT_CHARS`?
     3. Como `PromptLoader` resuelve el archivo segun la version?
     4. Que delimiters y escapes usa `ContextBuilder` para evitar inyeccion?
     5. Como se corta el contexto cuando supera el limite?
     6. El prompt v1 incluye reglas explicitas de seguridad? Ver `v1_answer_es.md`.
     7. Existe un prompt v2 en `backend/app/prompts`? Si no, TODO/Planned.
   - Checkpoint:
     - Se donde se define el prompt y su version.
     - Se como se arma y limita el contexto.
     - Se donde viven las defensas basicas.

10. <a id="backend-auth-scopes-rate-limit-metrics-logging-middleware"></a>Backend: auth, scopes, rate limit, metrics, logging, middlewares
    - Objetivo: Ubicar controles de seguridad y observabilidad.
    - Que necesito tener abierto:
      - `backend/app/auth.py`
      - `backend/app/rate_limit.py`
      - `backend/app/middleware.py`
      - `backend/app/metrics.py`
      - `backend/app/logger.py`
      - `backend/app/security.py`
      - `backend/app/main.py`
    - Preguntas:
      1. Donde se parsea `API_KEYS_CONFIG` y que formato espera?
      2. Que scopes se exigen en `routes.py` para `ingest` y `ask`?
      3. Como `RateLimitMiddleware` identifica clientes y que headers agrega?
      4. Que rutas excluye del rate limit?
      5. Que metricas expone `metrics.py` y con que labels?
      6. Que hace `RequestContextMiddleware` y que header agrega?
      7. Se registra `SecurityHeadersMiddleware` en `main.py`? Si no, TODO/Planned.
      8. Se aplica `require_metrics_auth` en `/metrics`? Si no, TODO/Planned.
    - Checkpoint:
      - Se donde esta auth, rate limit y metrics.
      - Se que middlewares corren y que headers agregan.
      - Se si faltan wiring de seguridad.

11. <a id="frontend-app-router-hooks-components"></a>Frontend: estructura App Router, hooks, components
    - Objetivo: Mapear la UI y sus piezas.
    - Que necesito tener abierto:
      - `frontend/app/layout.tsx`
      - `frontend/app/page.tsx`
      - `frontend/app/error.tsx`
      - `frontend/app/loading.tsx`
      - `frontend/app/components`
      - `frontend/app/hooks/useRagAsk.ts`
    - Preguntas:
      1. Que metadata se define en `layout.tsx`?
      2. Que componentes renderiza `page.tsx` y en que orden?
      3. Que hace el error boundary en `error.tsx`?
      4. Que muestra el loading UI en `loading.tsx`?
      5. Que componentes existen en `frontend/app/components` y que props requieren?
      6. Que estado maneja `useRagAsk.ts` y que API expone?
    - Checkpoint:
      - Se como se compone la pagina principal.
      - Se donde vive el manejo de errores y loading.
      - Se que componentes y hooks existen.

12. <a id="frontend-api-rewrites-config-env-errores"></a>Frontend: API rewrites/config/env vars + manejo de errores
    - Objetivo: Entender como el frontend llega al backend.
    - Que necesito tener abierto:
      - `frontend/next.config.ts`
      - `frontend/next.config.mjs`
      - `.env.example`
      - `frontend/app/hooks/useRagAsk.ts`
      - `frontend/app/components/StatusBanner.tsx`
    - Preguntas:
      1. Que rewrite define `next.config.ts` y que env var usa?
      2. Que rewrite define `next.config.mjs` y esta en sync con el `.ts`?
      3. Donde se documenta `NEXT_PUBLIC_API_URL` y cual es el default?
      4. Que codigos de estado mapea `useRagAsk.ts` a mensajes?
      5. Donde se muestra el error en la UI (ver `StatusBanner.tsx`)?
      6. Se envia `X-API-Key` desde el frontend? Si no, TODO/Planned.
      7. Como se maneja timeout/abort en `useRagAsk.ts`?
    - Checkpoint:
      - Se como funciona el proxy `/v1/*`.
      - Se como se muestran errores en UI.
      - Se si hay pendiente para API key en frontend.

13. <a id="contracts-openapi-orval-regeneracion"></a>Contracts: OpenAPI export, Orval, @contracts, regeneracion
    - Objetivo: Entender el pipeline de contratos compartidos.
    - Que necesito tener abierto:
      - `backend/scripts/export_openapi.py`
      - `shared/contracts/openapi.json`
      - `shared/contracts/orval.config.ts`
      - `shared/contracts/package.json`
      - `shared/contracts/src/generated.ts`
      - `package.json`
      - `.github/workflows/ci.yml`
    - Preguntas:
      1. Que hace `export_openapi.py` y que parametro requiere?
      2. Donde se guarda el OpenAPI exportado?
      3. Como `orval.config.ts` genera `src/generated.ts`?
      4. Que comandos root ejecutan export y gen (`package.json`)?
      5. Donde se usa `@contracts` en el frontend?
      6. Que job de CI valida que `shared/contracts` este actualizado?
    - Checkpoint:
      - Se como exportar OpenAPI y regenerar contratos.
      - Puedo ubicar el cliente TS generado.
      - Se como CI valida contracts.

14. <a id="ci-workflows"></a>CI: workflows (jobs, comandos exactos, por que falla cada uno)
    - Objetivo: Identificar jobs y condiciones de fallo.
    - Que necesito tener abierto:
      - `.github/workflows/ci.yml`
      - `backend/requirements.txt`
      - `frontend/package.json`
      - `shared/contracts/package.json`
    - Preguntas:
      1. Que jobs existen en `ci.yml` y en que orden corren (needs)?
      2. Que comandos exactos corre `backend-lint` y `backend-test`?
      3. Que servicios/env necesita `backend-test` para pasar?
      4. Que comandos exactos corre `frontend-lint` y `frontend-test`?
      5. Que pasos corren `contracts-check` y que diff valida?
      6. Que pasos usan `codecov` y que archivos suben?
      7. Que fallaria si cambian los lockfiles o el coverage?
    - Checkpoint:
      - Puedo reproducir localmente cada job.
      - Se que dependencias requiere cada job.
      - Se que condiciones hacen fallar CI.

15. <a id="dependabot-mantenimiento"></a>Dependabot y reglas de mantenimiento
    - Objetivo: Saber que dependencias se actualizan automatico.
    - Que necesito tener abierto:
      - `.github/dependabot.yml`
    - Preguntas:
      1. Que ecosistemas monitorea Dependabot y en que directorios?
      2. Con que frecuencia corre cada update y que limite de PRs hay?
      3. Que labels agrega para python, javascript y contracts?
      4. Hay agrupaciones de updates (`groups`)? Cuales?
      5. Se actualizan dependencias del root `package.json`? Si no, TODO/Planned.
    - Checkpoint:
      - Se que paquetes se actualizan automaticamente.
      - Se que reglas y labels aplica Dependabot.
      - Se si falta cubrir el root.

16. <a id="docs-actualizado-vs-drifted"></a>Docs del repo: que esta actualizado vs que esta drifted (lista de checks/preguntas)
    - Objetivo: Detectar inconsistencias entre docs y codigo.
    - Que necesito tener abierto:
      - `README.md`
      - `doc/README.md`
      - `doc/api/http-api.md`
      - `doc/runbook/local-dev.md`
      - `doc/architecture/overview.md`
      - `doc/data/postgres-schema.md`
      - `backend/app/rate_limit.py`
      - `backend/app/auth.py`
      - `frontend/__tests__`
      - `frontend/next.config.ts`
    - Preguntas:
      1. `README.md` dice que auth/rate limit son "planificado"; coincide con `auth.py` y `rate_limit.py`?
      2. `README.md` dice que tests frontend son TODO; coincide con `frontend/__tests__` y `frontend/package.json`?
      3. `doc/api/http-api.md` menciona `/api/v1`; coincide con `backend/app/versioning.py`?
      4. `doc/runbook/local-dev.md` define `NEXT_PUBLIC_API_URL`; coincide con `next.config.ts` default?
      5. `doc/architecture/overview.md` menciona prompts v2; existe el archivo?
      6. `doc/data/postgres-schema.md` refleja las columnas reales de `infra/postgres/init.sql`?
      7. `doc/README.md` tiene `Last Updated` consistente con cambios recientes?
      8. Hay docs sobre `compose.observability.yaml` en `doc/runbook/local-dev.md`? Si no, TODO/Planned.
    - Checkpoint:
      - Tengo una lista clara de potenciales drifts.
      - Puedo priorizar que docs actualizar.
      - Se donde buscar inconsistencias.

17. <a id="cambios-tipicos-playbook"></a>"Cambios tipicos" y como no romper nada (playbook de preguntas)
    - Objetivo: Tener un checklist mental antes de cambiar algo.
    - Que necesito tener abierto:
      - `backend/app/routes.py`
      - `backend/scripts/export_openapi.py`
      - `shared/contracts/openapi.json`
      - `shared/contracts/src/generated.ts`
      - `infra/postgres/init.sql`
      - `doc/api/http-api.md`
      - `doc/data/postgres-schema.md`
      - `doc/runbook/local-dev.md`
      - `.env.example`
    - Preguntas:
      1. Si agrego un endpoint, que archivos debo tocar y que contratos regenerar?
      2. Si cambio request/response, que comandos debo correr para actualizar `shared/contracts`?
      3. Si cambio el schema en `init.sql`, que repositorios y docs debo actualizar?
      4. Si cambio limites en `backend/app/config.py`, donde actualizo `.env.example` y docs?
      5. Si cambio prompts en `backend/app/prompts`, que version debo ajustar?
      6. Si cambio el proxy `/v1/*` del frontend, que config y docs debo tocar?
      7. Si agrego un servicio en compose, que runbook y docs debo actualizar?
    - Checkpoint:
      - Se que pasos seguir para cambios comunes.
      - Se que docs y contratos actualizar.
      - Se como evitar romper CI.

18. <a id="preguntas-de-auditoria"></a>Preguntas de auditoria
    - Objetivo: Auditar coherencia entre piezas del repo.
    - Que necesito tener abierto:
      - `backend/app/routes.py`
      - `backend/app/main.py`
      - `backend/app/versioning.py`
      - `shared/contracts/openapi.json`
      - `frontend/app/hooks/useRagAsk.ts`
      - `frontend/next.config.ts`
      - `compose.yaml`
      - `compose.prod.yaml`
      - `compose.observability.yaml`
      - `infra/postgres/init.sql`
      - `backend/app/infrastructure/repositories/postgres_document_repo.py`
      - `backend/app/config.py`
      - `backend/app/auth.py`
      - `backend/app/rate_limit.py`
      - `backend/app/security.py`
      - `backend/app/tracing.py`
      - `backend/app/prompts/v1_answer_es.md`
      - `doc/api/http-api.md`
      - `doc/runbook/local-dev.md`
      - `doc/data/postgres-schema.md`
      - `README.md`
      - `backend/pytest.ini`
      - `.github/workflows/ci.yml`
    - Preguntas:
      1. Las rutas en `backend/app/routes.py` coinciden con las rutas en `shared/contracts/openapi.json`?
      2. `openapi.json` incluye `/v1/ingest/text`, `/v1/ingest/batch`, `/v1/query`, `/v1/ask`?
      3. `openapi.json` incluye rutas `/api/v1/*` generadas por `versioning.py`?
      4. La seguridad `X-API-Key` en `backend/app/main.py` aparece en el OpenAPI exportado?
      5. `frontend/app/hooks/useRagAsk.ts` usa `askV1AskPost`; coincide con el path de OpenAPI?
      6. `frontend/next.config.ts` reescribe `/v1/*`; coincide con `openapi.json`?
      7. `compose.yaml` puertos 8000/5432 coinciden con `doc/runbook/local-dev.md`?
      8. `compose.prod.yaml` healthcheck usa `/health`; existe en `backend/app/main.py`? Si no, TODO/Planned.
      9. `compose.observability.yaml` apunta a `postgres:5432` para el exporter; donde se define ese servicio/red?
      10. `infra/postgres/init.sql` incluye `deleted_at`? coincide con `soft_delete_document`?
      11. `PostgresDocumentRepository` valida dimension 768; coincide con `VECTOR(768)` en schema?
      12. `backend/app/config.py` requiere `GOOGLE_API_KEY`; en CI se setea `fake-key-for-tests` y hay tests que lo usan?
      13. `rate_limit.py` excluye `/metrics`; coincide con `doc/api/http-api.md`?
      14. `auth.py` scopes (`ingest`, `ask`, `metrics`) coinciden con docs?
      15. `SecurityHeadersMiddleware` no aparece en `main.py`; esta documentado en alguna parte?
      16. `tracing.py` se habilita con `OTEL_ENABLED`; esta documentado en `.env.example` y `doc/runbook/local-dev.md`?
      17. `backend/app/prompts/v1_answer_es.md` coincide con la descripcion en `doc/architecture/overview.md`?
      18. `backend/app/infrastructure/text/semantic_chunker.py` esta usado en `container.py`?
      19. `frontend/__tests__` coincide con lo que dice `README.md` sobre tests?
      20. `backend/pytest.ini` define `cov-fail-under=70`; `ci.yml` usa `pytest --cov=app --cov-report=xml -q`: se espera que falle si baja la cobertura?
      21. `shared/contracts/openapi.json` se regenera en CI y se valida con `git diff --exit-code`; hay scripts locales equivalentes?
      22. `frontend/next.config.mjs` y `next.config.ts` estan alineados o generan comportamiento distinto?
      23. `doc/data/postgres-schema.md` y `infra/postgres/init.sql` estan alineados en indices y columnas?
      24. `doc/runbook/local-dev.md` y `package.json` usan los mismos comandos (`pnpm docker:up`, `pnpm dev`, `pnpm contracts:*`)?
    - Checkpoint:
      - Tengo una lista de inconsistencias a revisar.
      - Puedo cruzar contratos, rutas y docs.
      - Se que gaps de observability y seguridad revisar.

19. <a id="preguntas-refactors-futuros-no-ejecutar"></a>Preguntas para refactors futuros (no ejecutar)
    - Objetivo: Identificar oportunidades de mejora sin tocar codigo.
    - Que necesito tener abierto:
      - `frontend/next.config.ts`
      - `frontend/next.config.mjs`
      - `backend/app/security.py`
      - `backend/app/main.py`
      - `backend/app/streaming.py`
      - `backend/app/domain/services.py`
      - `backend/app/versioning.py`
      - `backend/app/infrastructure/text/semantic_chunker.py`
      - `backend/app/infrastructure/repositories/postgres_document_repo.py`
      - `infra/postgres/init.sql`
    - Preguntas:
      1. Conviene eliminar el duplicado entre `frontend/next.config.mjs` y `frontend/next.config.ts`?
      2. Conviene registrar `SecurityHeadersMiddleware` en `backend/app/main.py`?
      3. Conviene exponer un endpoint SSE usando `backend/app/streaming.py` y `LLMService.generate_stream`?
      4. Conviene unificar `/v1` y `/api/v1` para evitar duplicacion?
      5. Conviene agregar columna `deleted_at` en schema o remover `soft_delete_document`?
      6. Conviene agregar un selector de chunker (simple vs semantic) en `container.py`?
      7. Conviene mockear `GoogleEmbeddingService`/`GoogleLLMService` en tests para no requerir key?
      8. Conviene agregar UI de ingest en `frontend/app`?
      9. Conviene mover `NEXT_PUBLIC_API_URL` a una sola fuente y borrar el `.mjs`?
      10. Conviene versionar prompts con `v2` real y tests de prompt?
      11. Conviene activar `require_metrics_auth` cuando `METRICS_REQUIRE_AUTH=true`?
      12. Conviene unificar observability en un solo `compose.yaml` con profiles?
    - Checkpoint:
      - Tengo una lista de refactors priorizables.
      - Se que archivos tocar si se aprueban.
      - No ejecuto cambios sin decision.
