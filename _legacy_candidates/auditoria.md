# Auditoría Completa - RAG Corp

**Fecha de Auditoría**: 2 de Enero, 2026  
**Objetivo**: Entender el estado actual del proyecto sin modificar archivos  
**Auditor**: GitHub Copilot  

---

## 1) Resumen de Arquitectura

### Componentes Principales

**Frontend (Next.js)**
- **Ubicación**: `apps/web`
- **Responsabilidad**: Interfaz de usuario para consultas RAG
- **Tecnología**: Next.js 16.1.1 (App Router), Tailwind CSS 4, TypeScript
- **Punto de entrada**: `apps/web/app/page.tsx`

**Backend (FastAPI)**
- **Ubicación**: `services/rag-api`
- **Responsabilidad**: Orquestar el flujo RAG completo
- **Tecnología**: Python 3.11, FastAPI, psycopg
- **Punto de entrada**: `services/rag-api/app/main.py`

**Base de Datos Vectorial**
- **Tecnología**: PostgreSQL 16 + pgvector 0.8.1
- **Schema**: `infra/postgres/init.sql`
- **Responsabilidad**: Almacenar documentos, chunks y embeddings (768D)

**Servicios Externos**
- **Google Gemini**: Embeddings (text-embedding-004) y generación de respuestas (Gemini 1.5 Flash)
- **Implementaciones**: `services/rag-api/app/infrastructure/services`

### Flujo de Datos Principal

**Ingesta** (`POST /v1/ingest/text`):
1. Controller recibe documento (`services/rag-api/app/routes.py` línea 60)
2. Use case `IngestDocumentUseCase` orquesta:
   - Chunking (900 chars, 120 overlap) vía `SimpleTextChunker`
   - Embeddings batch vía `GoogleEmbeddingService`
   - Persistencia vía `PostgresDocumentRepository`
3. Retorna `document_id` y count de chunks

**Retrieval + Generation** (`POST /v1/ask`):
1. Controller recibe query (`services/rag-api/app/routes.py` línea 116)
2. Use case `AnswerQueryUseCase` ejecuta:
   - **Embed query** (línea 96): convierte texto a vector 768D
   - **Retrieve chunks** (línea 99): busca top-k similares en PostgreSQL con cosine distance
   - **Assemble context** (línea 117): concatena contenido de chunks
   - **Generate answer** (línea 121): envía query + context a Gemini
3. Retorna `QueryResult` con respuesta y fuentes

### Arquitectura de Capas (Clean Architecture)

```
┌─────────────────────────────────────┐
│  API Layer (FastAPI)                │  routes.py, main.py
├─────────────────────────────────────┤
│  Application (Use Cases)            │  answer_query.py, ingest_document.py
├─────────────────────────────────────┤
│  Domain (Entities + Protocols)      │  entities.py, repositories.py, services.py
├─────────────────────────────────────┤
│  Infrastructure (Adapters)          │  postgres_document_repo.py, google_*_service.py
└─────────────────────────────────────┘
```

---

## 2) Mapa de Carpetas

### Raíz del Proyecto

| Carpeta/Archivo | Propósito | Evidencia |
|-----------------|-----------|-----------|
| `apps/web` | Frontend Next.js | `apps/web/README.md` |
| `services/rag-api` | Backend FastAPI | `services/rag-api/app/main.py` |
| `packages/contracts` | Contratos compartidos (OpenAPI → TS) | `packages/contracts/orval.config.ts` |
| `infra/postgres` | DDL y setup de base de datos | `infra/postgres/init.sql` |
| `doc` | Documentación técnica | `doc/README.md` |
| `_legacy_candidates` | Archivos deprecados | `_legacy_candidates/README.md` |
| `compose.yaml` | Orquestación Docker | `compose.yaml` |
| `.env.example` | Template de configuración | `.env.example` |
| `FIXES.md` | Histórico de correcciones | `FIXES.md` |

### Backend (`services/rag-api/app`)

| Carpeta | Rol | Archivos Clave |
|---------|-----|----------------|
| `domain/` | **Núcleo de negocio** (entidades, interfaces) | `services/rag-api/app/domain/entities.py`, `services/rag-api/app/domain/repositories.py`, `services/rag-api/app/domain/services.py` |
| `application/use_cases/` | **Orquestación** de flujos RAG | `services/rag-api/app/application/use_cases/answer_query.py`, `services/rag-api/app/application/use_cases/ingest_document.py` |
| `infrastructure/` | **Adapters** (DB, APIs, chunking) | `repositories/`, `services/` |
| `routes.py` | **Controllers** HTTP | `services/rag-api/app/routes.py` |
| `container.py` | **Dependency Injection** | `services/rag-api/app/container.py` |
| `exceptions.py` | Jerarquía de excepciones | `services/rag-api/app/exceptions.py` |
| `logger.py` | Logging estructurado JSON | `services/rag-api/app/logger.py` |

### Tests (`services/rag-api/tests`)

| Carpeta | Cobertura | Dependencias Externas |
|---------|-----------|----------------------|
| `unit/` | Use cases, entidades | ❌ Ninguna (mocks) |
| `integration/` | Repositorio PostgreSQL | ✅ Requiere DB + API key |
| `conftest.py` | Fixtures compartidas | `services/rag-api/tests/conftest.py` |

---

## 3) Evaluación de Buenas Prácticas

### ✅ Fortalezas

**Separación de Capas**
- ✅ Clean Architecture implementada correctamente (domain/, application/, infrastructure/)
- ✅ Use cases aislados y testeables (`services/rag-api/app/application/use_cases/answer_query.py`)
- ✅ Dependency injection explícita (`services/rag-api/app/container.py`)

**Contratos y Tipado**
- ✅ OpenAPI como fuente de verdad (`packages/contracts/openapi.json`)
- ✅ Cliente TypeScript autogenerado con Orval (`packages/contracts/src/generated.ts`)
- ✅ Type hints en Python (≥90% cobertura estimada)
- ✅ Pydantic models para validación (`services/rag-api/app/routes.py`)

**Documentación**
- ✅ CRC Cards en código (responsabilidades claras)
- ✅ README completo con quickstart (`README.md`)
- ✅ Documentación técnica organizada (`doc`)
- ✅ Comentarios explicativos con rationale ("R: ...")

**Testing**
- ✅ Suite de tests documentada (tests/README.md)
- ✅ Separación unit/integration
- ✅ Mocks para dependencias externas (`services/rag-api/tests/conftest.py`)

### ⚠️ Áreas de Mejora

**Manejo de Errores**
- ⚠️ Exception handlers básicos (`services/rag-api/app/main.py` líneas 53-78)
- ❌ No hay retry logic para fallos transitorios (DB, Google API)
- ❌ Falta validación de dimensión de embeddings (esperados: 768)

**Configuración**
- ❌ Hardcoded values (`services/rag-api/app/main.py` línea 42: `allow_origins=["http://localhost:3000"]`)
- ⚠️ API key global en lugar de instancia (`services/rag-api/app/infrastructure/services/google_embedding_service.py`)
- ❌ No hay validación de variables de entorno requeridas al inicio

**Logging/Observabilidad**
- ✅ Structured logging JSON (`services/rag-api/app/logger.py`)
- ❌ No hay métricas (latencia, throughput)
- ❌ No hay tracing distribuido (correlación de requests)
- ❌ Logs incompletos en casos de error (faltan stacktraces en algunos handlers)

**Seguridad**
- ❌ Sin autenticación/autorización
- ❌ Sin rate limiting
- ❌ CORS permisivo (development only, pero falta TODO para producción)
- ⚠️ API key en variable de entorno (correcto), pero no hay rotación

**Performance**
- ⚠️ Conexiones DB no pooled (`services/rag-api/app/infrastructure/repositories/postgres_document_repo.py` línea 55: crea nueva conexión por operación)
- ⚠️ Embeddings batch limitados a 10 (`services/rag-api/app/infrastructure/services/google_embedding_service.py`)
- ❌ No hay caché para embeddings de queries frecuentes

---

## 4) Deuda Técnica Priorizada (Top 10)

### 🔴 Impacto Alto

**1. Conexiones DB sin pooling**
- **Problema**: Cada operación crea nueva conexión (`services/rag-api/app/infrastructure/repositories/postgres_document_repo.py` línea 55)
- **Impacto**: Latencia alta (100-200ms overhead por query), riesgo de "too many connections"
- **Evidencia**: `self._conn()` crea `psycopg.connect()` en cada llamada
- **Solución**: Implementar `psycopg_pool.ConnectionPool`

**2. API Key de Google configurada globalmente**
- **Problema**: `genai.configure()` es global (`services/rag-api/app/infrastructure/services/google_embedding_service.py` línea 44)
- **Impacto**: No permite multi-tenancy, dificulta testing
- **Evidencia**: `genai.configure(api_key=api_key)` en `__init__`
- **Solución**: Inyectar API key por instancia o usar contexto

**3. Sin validación de dimensión de embeddings**
- **Problema**: No se verifica que embeddings sean 768D antes de insertar
- **Impacto**: Corrupción silenciosa de datos si Google cambia modelo
- **Evidencia**: `services/rag-api/app/infrastructure/repositories/postgres_document_repo.py` línea 97 inserta sin validar
- **Solución**: Assertion en `save_chunks()` y test de integración

**4. CORS hardcoded para desarrollo**
- **Problema**: `allow_origins=["http://localhost:3000"]` (`services/rag-api/app/main.py` línea 42)
- **Impacto**: No funciona en staging/production sin cambio de código
- **Evidencia**: Comentario "TODO: Read ALLOWED_ORIGINS from .env" (línea 27)
- **Solución**: Variable de entorno `ALLOWED_ORIGINS` (CSV)

### 🟡 Impacto Medio

**5. No hay retry logic para servicios externos**
- **Problema**: Fallos HTTP 429 (rate limit) o timeouts no se reintentan
- **Impacto**: Errores transitorios causan fallos permanentes
- **Evidencia**: `services/rag-api/app/infrastructure/services/google_embedding_service.py` y `services/rag-api/app/infrastructure/services/google_llm_service.py` no usan decorador `@retry`
- **Solución**: Librería `tenacity` con exponential backoff

**6. Health check no verifica Google API**
- **Problema**: `/healthz` solo valida DB (`services/rag-api/app/main.py` línea 94)
- **Impacto**: Sistema puede reportar "healthy" sin poder generar respuestas
- **Evidencia**: Falta llamada a `embedding_service.embed_query("test")`
- **Solución**: Agregar check opcional de Google API (timeout 5s)

**7. Logs sin context ID de request**
- **Problema**: No hay `request_id` en logs estructurados (`services/rag-api/app/logger.py`)
- **Impacto**: Difícil correlacionar logs de una misma request
- **Evidencia**: JSON logs no incluyen `request_id` field
- **Solución**: Middleware que inyecta UUID en contexto

**8. Tests de integración no limpian datos automáticamente**
- **Problema**: Cleanup manual en fixtures (`services/rag-api/tests/integration/test_postgres_document_repo.py` línea 47)
- **Impacto**: Tests pueden fallar si se ejecutan fuera de orden
- **Evidencia**: `cleanup_test_data` es fixture explícita, no automática
- **Solución**: Usar transacciones con rollback automático

### 🟢 Impacto Bajo

**9. Documentación de errores incompleta**
- **Problema**: `doc/api/http-api.md` no lista todos los códigos de error
- **Impacto**: Desarrolladores frontend deben inspeccionar código
- **Evidencia**: Falta sección "Error Catalog" con códigos 400/422/503
- **Solución**: Generar tabla de errores desde `services/rag-api/app/exceptions.py`

**10. Frontend sin tests automatizados**
- **Problema**: No hay suite de tests en `apps/web`
- **Impacto**: Regresiones no detectadas en UI
- **Evidencia**: No existe `apps/web/__tests__/` ni scripts de test en `apps/web/package.json`
- **Solución**: Setup Jest + React Testing Library

---

## 5) Quick Wins y Mejoras Medianas

### ⚡ Quick Wins (1-2 horas c/u)

**QW1: Agregar validación de env vars al inicio**
```python
# services/rag-api/app/main.py (después de imports)
required_env_vars = ["DATABASE_URL", "GOOGLE_API_KEY"]
missing = [v for v in required_env_vars if not os.getenv(v)]
if missing:
    raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
```
- **Beneficio**: Fail-fast en lugar de errores crípticos después
- **Testing**: Correr sin `.env` y verificar error claro

**QW2: Mover CORS origins a variable de entorno**
```python
# services/rag-api/app/main.py
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    ...
)
```
- **Archivo**: `services/rag-api/app/main.py` línea 42
- **Testing**: Setear `ALLOWED_ORIGINS=http://example.com` y verificar

**QW3: Agregar request_id a logs**
```python
# services/rag-api/app/main.py (nuevo middleware)
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    logger.info(f"Request started | request_id={request_id} | path={request.url.path}")
    response = await call_next(request)
    logger.info(f"Request completed | request_id={request_id} | status={response.status_code}")
    return response
```
- **Beneficio**: Trazabilidad end-to-end
- **Testing**: Verificar que logs incluyan `request_id` field

**QW4: Validar dimensión de embeddings**
```python
# services/rag-api/app/infrastructure/repositories/postgres_document_repo.py
def save_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None:
    for chunk in chunks:
        if len(chunk.embedding) != 768:
            raise ValueError(f"Invalid embedding dimension: {len(chunk.embedding)}")
    # ...existing code...
```
- **Archivo**: `services/rag-api/app/infrastructure/repositories/postgres_document_repo.py` línea 97
- **Testing**: Agregar unit test con embedding de 512D

### 🔧 Mejoras Medianas (1-2 días c/u)

**MM1: Implementar connection pooling**
```python
# services/rag-api/app/infrastructure/repositories/postgres_document_repo.py
from psycopg_pool import ConnectionPool

class PostgresDocumentRepository:
    _pool: ConnectionPool = None
    
    @classmethod
    def initialize_pool(cls):
        if cls._pool is None:
            cls._pool = ConnectionPool(os.getenv("DATABASE_URL"), min_size=2, max_size=10)
    
    def _conn(self):
        return self._pool.connection()
```
- **Pasos**:
  1. Instalar `psycopg-pool`
  2. Modificar `services/rag-api/app/infrastructure/repositories/postgres_document_repo.py`
  3. Inicializar pool en `services/rag-api/app/main.py` startup event
  4. Benchmark antes/después (10 queries secuenciales)
- **Testing**: Integration tests deben seguir pasando

**MM2: Agregar retry logic con tenacity**
```python
# services/rag-api/app/infrastructure/services/google_embedding_service.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed_query(self, text: str) -> List[float]:
    # ...existing code...
```
- **Archivos**: `services/rag-api/app/infrastructure/services/google_embedding_service.py`, `services/rag-api/app/infrastructure/services/google_llm_service.py`
- **Pasos**:
  1. `pip install tenacity`
  2. Decorar métodos que llaman APIs externas
  3. Agregar logging de retries
  4. Unit test simulando HTTP 429
- **Testing**: Mock que falla 2 veces y luego responde

**MM3: Mejorar health check**
```python
# services/rag-api/app/main.py
@app.get("/healthz")
def healthz():
    checks = {"db": "unknown", "google_api": "unknown"}
    
    # Check DB
    try:
        repo = get_document_repository()
        with repo._conn() as conn:
            conn.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {str(e)}"
    
    # Check Google API (optional, timeout 5s)
    try:
        embedding_service = get_embedding_service()
        embedding_service.embed_query("health check")
        checks["google_api"] = "ok"
    except Exception as e:
        checks["google_api"] = f"error: {str(e)}"
    
    return {"ok": all(v == "ok" for v in checks.values()), "checks": checks}
```
- **Beneficio**: Detectar degradación antes que usuarios
- **Testing**: Apagar DB y verificar respuesta

**MM4: Setup tests frontend**
```bash
cd apps/web
pnpm add -D jest @testing-library/react @testing-library/jest-dom
```
- **Crear**: `apps/web/jest.config.js`, `apps/web/__tests__/page.test.tsx`
- **Script**: `"test": "jest"` en `apps/web/package.json`
- **Testing**: Test básico de render de componentes

---

## 6) Checklist para Correr Local

### Requisitos Previos
- ✅ Node.js 20.9+ y pnpm 10+
- ✅ Docker y Docker Compose
- ✅ Cuenta Google Cloud con Gemini API habilitada

### Paso a Paso

**1. Clonar y configurar entorno**
```bash
git clone https://github.com/SaintWyss/rag-corp.git
cd rag-corp
cp .env.example .env
# Editar .env y agregar GOOGLE_API_KEY
```
- **Referencia**: `README.md` líneas 80-88

**2. Instalar dependencias**
```bash
pnpm install
```
- **Referencia**: `README.md` línea 93

**3. Levantar infraestructura**
```bash
pnpm docker:up
# Esperar ~30s para que PostgreSQL inicie
docker compose ps  # Verificar que todo esté "Up"
```
- **Referencia**: `README.md` líneas 99-103
- **Verificación**: `psql postgresql://postgres:postgres@localhost:5432/rag -c "SELECT 1"`

**4. Generar contratos TypeScript**
```bash
pnpm contracts:export
pnpm contracts:gen
```
- **Referencia**: `README.md` líneas 108-112
- **Output esperado**: `packages/contracts/openapi.json` y `packages/contracts/src/generated.ts` actualizados

**5. Ejecutar en desarrollo**
```bash
pnpm dev
```
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Referencia**: `README.md` líneas 117-125

### Verificación Final

**Health check**
```bash
curl http://localhost:8000/healthz
# Esperado: {"ok": true, "db": "connected"}
```

**Ingestar documento de prueba**
```bash
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Document",
    "text": "RAG Corp es un sistema de búsqueda semántica que usa embeddings vectoriales para recuperar documentos relevantes y generar respuestas contextuales.",
    "source": "test"
  }'
# Esperado: {"document_id": "...", "chunks": 1}
```

**Hacer consulta**
```bash
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es RAG Corp?", "top_k": 3}'
# Esperado: {"answer": "...", "sources": ["..."]}
```

### Troubleshooting

**Error: "connection refused" en DB**
```bash
docker compose logs db
docker compose restart db
```

**Error: "GOOGLE_API_KEY not configured"**
- Verificar que `.env` tenga la variable
- Reiniciar contenedor: `docker compose restart rag-api`

**Frontend no conecta al backend**
- Verificar proxy en `apps/web/next.config.ts`
- Verificar CORS en `services/rag-api/app/main.py`

**Tests fallan**
```bash
# Unit tests (no requieren deps externas)
cd services/rag-api
pytest -m unit

# Integration tests (requieren DB + API key)
RUN_INTEGRATION=1 GOOGLE_API_KEY=tu_clave pytest -m integration
```
- **Referencia**: tests/README.md

---

## Resumen Ejecutivo

**Estado General**: ✅ **Proyecto saludable y bien estructurado**

- Arquitectura limpia (Clean Architecture con capas bien definidas)
- Documentación completa y actualizada
- Suite de tests funcional (unit + integration)
- Contratos tipados entre FE/BE

**Principales Gaps**:
1. Performance (connection pooling, caché)
2. Observabilidad (métricas, tracing)
3. Resilencia (retry logic, health checks robustos)
4. Seguridad (autenticación, rate limiting)

**Recomendación**: Priorizar Quick Wins (QW1-QW4) en próxima sesión de desarrollo (4-6 horas total) antes de abordar mejoras medianas.

---

## Próximos Pasos Sugeridos

1. **Implementar Quick Wins** (Esta semana)
   - QW1: Validación env vars (30 min)
   - QW2: CORS configurable (20 min) 
   - QW3: Request ID en logs (45 min)
   - QW4: Validación embeddings (30 min)

2. **Mejoras Medianas** (Próximas 2 semanas)
   - MM1: Connection pooling (1 día)
   - MM2: Retry logic (0.5 días)
   - MM3: Health check robusto (0.5 días)

3. **Arquitectura Avanzada** (Mes próximo)
   - Autenticación/autorización
   - Métricas y observabilidad
   - Caché de embeddings
   - Tests frontend

**Criterio de Éxito**: Sistema listo para staging después de Quick Wins + MM1-MM2.