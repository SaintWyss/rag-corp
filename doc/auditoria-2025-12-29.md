# Auditoría Completa del Repositorio RAG Corp
**Fecha**: 29 de diciembre de 2025  
**Auditor**: GitHub Copilot (Claude Sonnet 4.5)  
**Solicitante**: Santiago

---

## Prompt Original

```
Quiero una auditoría completa del repo.

Objetivo: entender qué tenemos hoy. NO modifiques archivos todavía.

Entregables:
1) Resumen de arquitectura: componentes, responsabilidades, flujo de datos principal 
   (ingesta → embeddings → almacenamiento → retrieval → respuesta).
2) Mapa de carpetas: qué rol cumple cada carpeta y por qué existe.
3) Evaluación de buenas prácticas: separación de capas, naming, manejo de errores, 
   tipado/contratos, configuración, logging/observabilidad, seguridad, tests.
4) Deuda técnica priorizada: Top 10 issues (impacto alto → bajo) con evidencia 
   (rutas/archivos relevantes).
5) Quick wins (1–2 horas) y mejoras medianas (1–2 días), con pasos concretos.
6) Checklist para correr local (si lo encontrás en README/compose/scripts).

Formato:
- Usá bullets claros.
- Citá archivos/rutas exactas cuando afirmes algo.
- Explicámelo "para Santiago" (nivel estudiante de Ing. en Sistemas, pero con rigor).
```

---

## 1. Resumen de Arquitectura

### Componentes Principales

**Name**: RAG Corp  
**Responsibilities**: Sistema RAG (Retrieval-Augmented Generation) que permite ingestar documentos, buscarlos por similitud semántica y generar respuestas contextuales usando Google Gemini.  
**Collaborators**: PostgreSQL + pgvector, Google Generative AI API, Next.js frontend.  
**Constraints**: Monorepo con pnpm + Turbo, arquitectura cliente-servidor, embeddings de 768 dimensiones (Google text-embedding-004).

### Flujo de Datos Principal

```
INGESTA:
Usuario → Frontend → /v1/ingest/text → chunk_text() → embed_texts() → 
Store.upsert_document() + Store.insert_chunks() → PostgreSQL (documents + chunks)

CONSULTA (RAG Completo):
Usuario → Frontend → /v1/ask → embed_query() → Store.search() (similitud vectorial) → 
generate_rag_answer() (Gemini) → Respuesta al usuario
```

**Detalles técnicos**:
- **Chunking**: `services/rag-api/app/text.py` (900 chars, 120 overlap)
- **Embeddings**: `services/rag-api/app/embeddings.py` (Google embedding-004, 768D)
- **Storage**: `services/rag-api/app/store.py` (PostgreSQL + pgvector)
- **LLM**: `services/rag-api/app/llm.py` (Gemini 1.5 Flash)
- **API**: `services/rag-api/app/routes.py` (FastAPI)
- **Frontend**: `apps/web/app/page.tsx` (Next.js 15)

---

## 2. Mapa de Carpetas

```
rag-corp/
├── .github/
│   └── copilot-instructions.md       # Instrucciones de proyecto (SOLID, CRC, ADRs)
├── apps/
│   └── web/                           # Frontend Next.js
│       ├── app/
│       │   ├── globals.css            # Estilos Tailwind
│       │   ├── layout.tsx             # Layout raíz (fuentes Geist)
│       │   └── page.tsx               # UI principal (input + respuesta)
│       ├── next.config.ts             # Rewrites proxy a backend
│       └── package.json               # Deps: Next 15, React 19, Tailwind 4
├── services/
│   └── rag-api/                       # Backend FastAPI
│       ├── app/
│       │   ├── main.py                # App FastAPI + CORS
│       │   ├── routes.py              # Endpoints: /ingest/text, /query, /ask
│       │   ├── store.py               # Capa de datos (PostgreSQL + pgvector)
│       │   ├── embeddings.py          # Google Embedding API
│       │   ├── llm.py                 # Google Gemini (generación)
│       │   └── text.py                # Chunking
│       ├── scripts/
│       │   └── export_openapi.py      # Export OpenAPI spec
│       ├── Dockerfile                 # Imagen Python 3.11
│       └── requirements.txt           # Deps: FastAPI, psycopg, pgvector, google-generativeai
├── packages/
│   └── contracts/                     # Contratos TypeScript generados
│       ├── src/generated.ts           # Cliente fetch auto-generado (Orval)
│       ├── openapi.json               # Spec exportada desde FastAPI
│       └── orval.config.ts            # Config de generación
├── infra/
│   └── postgres/
│       └── init.sql                   # Schema inicial (documents + chunks + índice vectorial)
├── compose.yaml                       # Docker Compose (db + rag-api)
├── pnpm-workspace.yaml                # Configuración monorepo
├── turbo.json                         # Tareas Turbo (dev, build, lint)
├── .env.example                       # Template de variables (GOOGLE_API_KEY)
├── FIXES.md                           # Documentación de fixes aplicados
├── setup.sh                           # Script de bootstrap inicial
├── migrate_to_gemini.sh               # Migración desde embeddings dummy a Gemini
└── implement_chat.sh                  # Implementación de endpoint /ask
```

### Roles de Carpetas

- **apps/web**: Cliente React/Next.js que consume la API.
- **services/rag-api**: Servidor Python con lógica RAG.
- **packages/contracts**: Single source of truth de tipos compartidos.
- **infra/postgres**: DDL y configuración de base de datos.
- **Scripts raíz**: Automatización de setup/migración (legacy, no se usan en dev diario).

---

## 3. Evaluación de Buenas Prácticas

### ✅ Puntos Fuertes

#### Separación de capas
- **Backend**: `services/rag-api/app/routes.py` (controllers) → `services/rag-api/app/store.py` (data) → `services/rag-api/app/embeddings.py`/`services/rag-api/app/llm.py` (servicios).
- **Frontend**: UI (`apps/web/app/page.tsx`) → contrato tipado (`packages/contracts/src/generated.ts`).

#### Naming
- Nombres descriptivos: `chunk_text`, `embed_query`, `generate_rag_answer`.
- Convención estándar: snake_case (Python), camelCase (TS).

#### Contratos/Tipado
- OpenAPI generada desde FastAPI → Orval → cliente TypeScript tipado.
- Flujo: `pnpm contracts:export && pnpm contracts:gen`.

#### Configuración
- Variables de entorno centralizadas (`.env.example`).
- Docker Compose con health checks.

---

### ⚠️ Puntos Débiles

#### Manejo de errores
- **`services/rag-api/app/routes.py`**: No hay try/except en endpoints.
- **`services/rag-api/app/embeddings.py`**: Logs a stdout (`print`), no structured logging.
- **`apps/web/app/page.tsx`**: Error genérico "Error de conexión", no distingue 4xx vs 5xx.

#### Logging/Observabilidad
- No hay logger configurado (usa `print`).
- No hay tracing ni métricas.
- No hay health check detallado (solo `{"ok": True}`).

#### Seguridad
- CORS permite `*` methods/headers (OK para dev, NO para prod).
- API Key en variable de entorno (correcto), pero sin rotación ni secrets manager.
- No hay autenticación en endpoints.

#### Tests
- **No existen tests** en todo el repositorio.
- No hay fixtures, no hay CI/CD.

#### Documentación
- Buen uso de `FIXES.md` para histórico.
- Falta README en raíz del repo (solo boilerplate de create-next-app en `apps/web/README.md`).
- No hay ADRs en `doc/decisions/` (como piden las instrucciones de Copilot).

---

## 4. Deuda Técnica Priorizada (Top 10)

### 🔴 Impacto Alto

#### 1. Falta de tests automatizados
- **Evidencia**: No hay carpetas `tests/` ni archivos `*_test.py` / `*.test.ts`.
- **Impacto**: Regresiones invisibles, no se puede refactorizar con confianza.
- **Afecta**: Todo el sistema.

#### 2. Manejo de errores inexistente en API
- **Evidencia**: `services/rag-api/app/routes.py` no captura excepciones de `embed_texts()`, `store.search()`, etc.
- **Impacto**: Errores 500 sin contexto, difícil debug.
- **Ejemplo**: Si Google API falla, el usuario recibe stack trace crudo.

#### 3. Sin logging estructurado
- **Evidencia**: `services/rag-api/app/embeddings.py` línea 29: `print(f"Error embedding batch: {e}")`.
- **Impacto**: Logs no parseables, no se pueden agregar en Datadog/CloudWatch.
- **Solución**: Usar `structlog` o `python-json-logger`.

#### 4. CORS abierto en producción
- **Evidencia**: `services/rag-api/app/main.py` línea 10: `allow_origins=["http://localhost:3000"]`.
- **Impacto**: Si se deploya así, solo funciona en localhost. Si se cambia a `["*"]`, es un agujero de seguridad.
- **Solución**: Leer `ALLOWED_ORIGINS` desde `.env`.

---

### 🟡 Impacto Medio

#### 5. Sin autenticación en endpoints
- **Evidencia**: `services/rag-api/app/routes.py` no usa `Depends()` para auth.
- **Impacto**: Cualquiera puede ingestar/consultar.
- **Solución**: Implementar API keys o JWT.

#### 6. Falta README en raíz
- **Evidencia**: No existe `README.md` en `/`.
- **Impacto**: Nuevos devs no saben cómo empezar.
- **Solución**: Crear README con Quickstart + links a docs.

#### 7. Sin validación de rate limiting
- **Evidencia**: No hay middleware de throttling.
- **Impacto**: Un usuario puede saturar Google API o PostgreSQL.
- **Solución**: Usar `slowapi` o Redis + token bucket.

#### 8. Configuración de Next.js duplicada (legacy)
- **Evidencia**: Coexisten `apps/web/next.config.ts` y referencia a `apps/web/next.config.mjs` en `FIXES.md`.
- **Impacto**: Confusión sobre cuál es el activo.
- **Solución**: Eliminar `.mjs` si existe.

---

### 🟢 Impacto Bajo

#### 9. Scripts de migración en raíz
- **Evidencia**: `setup.sh`, `migrate_to_gemini.sh`, `implement_chat.sh`.
- **Impacto**: Clutter, no se usan en dev diario, pueden quedar outdated.
- **Solución**: Mover a `scripts/archive/` o documentar como "históricos".

#### 10. No hay índice en `documents.title`
- **Evidencia**: `infra/postgres/init.sql` solo indexa `chunks.embedding`.
- **Impacto**: Si en el futuro se buscan documentos por título, será lento.
- **Solución**: Agregar `CREATE INDEX ON documents(title)` si se va a usar.

---

## 5. Mejoras Priorizadas

### ⚡ Quick Wins (1–2 horas cada una)

#### QW1: Crear README en raíz
```markdown
# RAG Corp

Sistema RAG con Google Gemini, PostgreSQL + pgvector, y Next.js.

## Quickstart
1. `cp .env.example .env` → editar GOOGLE_API_KEY
2. `pnpm install`
3. `pnpm docker:up`
4. `pnpm contracts:export && pnpm contracts:gen`
5. `pnpm dev`

Ver [FIXES.md](FIXES.md) para troubleshooting.
```
- **Impacto**: Onboarding 10x más rápido.
- **Archivos**: Crear `README.md`.

#### QW2: Agregar structured logging básico
```python
# services/rag-api/app/logger.py
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
```
- Reemplazar todos los `print` por `logger.info/error`.
- **Impacto**: Logs parseables desde día 1.
- **Archivos**: `services/rag-api/app/embeddings.py`, `services/rag-api/app/llm.py`.

#### QW3: Agregar health check detallado
```python
# services/rag-api/app/main.py
@app.get("/healthz")
def healthz():
    try:
        store._conn().execute("SELECT 1")
        return {"ok": True, "db": "connected"}
    except:
        return {"ok": False, "db": "disconnected"}
```
- **Impacto**: Detectar problemas de DB en Kubernetes/monitoring.
- **Archivos**: `services/rag-api/app/main.py`.

#### QW4: Validar que `next.config.mjs` no existe
```bash
# Si existe, eliminarlo
rm apps/web/next.config.mjs
```
- **Impacto**: Evitar confusión.
- **Archivos**: Potencialmente `apps/web/next.config.mjs`.

#### QW5: Agregar `.env.example` completo
```bash
# .env.example
GOOGLE_API_KEY=your_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
ALLOWED_ORIGINS=http://localhost:3000
```
- **Impacto**: Documentar todas las variables requeridas.
- **Archivos**: `.env.example`.

---

### 🔧 Mejoras Medianas (1–2 días)

#### M1: Implementar manejo de errores robusto en API
- Crear custom exceptions (`RAGError`, `EmbeddingError`).
- Agregar `@app.exception_handler` en `services/rag-api/app/main.py`.
- Wrap endpoints en try/except y retornar JSONResponse con status codes apropiados.
- **Archivos**: `services/rag-api/app/routes.py`, `services/rag-api/app/main.py`.

#### M2: Agregar tests básicos
```python
# services/rag-api/tests/test_text.py
from app.text import chunk_text

def test_chunk_text_empty():
    assert chunk_text("") == []

def test_chunk_text_small():
    result = chunk_text("hola", chunk_size=10)
    assert result == ["hola"]
```
- Setup pytest + pytest-cov.
- Tests unitarios para `services/rag-api/app/text.py`, `services/rag-api/app/embeddings.py` (mock Google API), `services/rag-api/app/store.py` (mock psycopg).
- **Archivos nuevos**: `services/rag-api/tests/`, `services/rag-api/pytest.ini`.

#### M3: Configurar CORS dinámico
```python
# services/rag-api/app/main.py
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # ...
)
```
- **Archivos**: `services/rag-api/app/main.py`, `.env.example`.

#### M4: Implementar autenticación básica (API Key)
```python
# services/rag-api/app/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
import os

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Security(api_key_header)):
    if key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
```
- Aplicar a todos los endpoints excepto `/healthz`.
- **Archivos**: Nuevo `services/rag-api/app/auth.py`, `services/rag-api/app/routes.py`.

#### M5: Crear ADRs para decisiones arquitectónicas
- Documentar por qué se eligió Gemini vs OpenAI.
- Documentar estrategia de chunking (900/120).
- Documentar uso de pgvector vs alternativas (Pinecone, Weaviate).
- **Archivos nuevos**: 
  - `doc/decisions/001-gemini-as-llm.md`
  - `doc/decisions/002-chunking-strategy.md`
  - `doc/decisions/003-pgvector-storage.md`

---

## 6. Checklist para Correr Local

### Prerequisitos
- pnpm 10.x
- Docker + Docker Compose
- Cuenta de Google Cloud con Gemini API habilitada

### Pasos (según `FIXES.md`)

```bash
# 1. Clonar repo
git clone <repo-url>
cd rag-corp

# 2. Configurar API Key
cp .env.example .env
# Editar .env y agregar: GOOGLE_API_KEY=tu_clave_aqui

# 3. Instalar dependencias
pnpm install

# 4. Levantar infraestructura
pnpm docker:up
# Esperar a que PostgreSQL esté healthy

# 5. Generar contratos TypeScript
pnpm contracts:export  # Exporta OpenAPI desde FastAPI
pnpm contracts:gen     # Genera cliente con Orval

# 6. Ejecutar en modo desarrollo
pnpm dev
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Troubleshooting
- **Error CORS**: Verificar `services/rag-api/app/main.py` línea 10.
- **Error 500 en /ask**: Verificar `GOOGLE_API_KEY` en `.env` y reiniciar `pnpm docker:down && pnpm docker:up`.
- **Base de datos no conecta**: Verificar que `docker compose ps` muestra `db` como `healthy`.

### Para Resetear DB
```bash
pnpm docker:down  # Destruye volúmenes
pnpm docker:up    # Recrea desde init.sql
```

---

## Conclusiones

### Estado actual
MVP funcional con arquitectura clara, pero sin tests, logging, ni seguridad para producción.

### Prioridad inmediata
1. README en raíz (15 min).
2. Structured logging (1 hora).
3. Manejo de errores en API (4 horas).
4. Tests unitarios básicos (1 día).

### Riesgo mayor
Sin tests, cualquier refactor puede romper silenciosamente el flujo RAG.

### Fortalezas
- Separación de capas clara
- Contratos tipados
- Docker Compose funcional
- Documentación de fixes aplicados

---

## Siguientes Pasos Recomendados

1. **Implementar Quick Wins 1-3** (mañana, 3 horas total)
2. **M1 + M2** (esta semana, 2 días)
3. **M3 + M4** (próxima semana, 1-2 días)
4. **Configurar CI/CD** con GitHub Actions para correr tests + lint
5. **Crear ADRs** documentando decisiones tomadas hasta ahora

---

**Fin del Documento**
