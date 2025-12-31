# Registro de Cambios del Chat

Objetivo: dejar trazabilidad tecnica de lo realizado en este chat, con motivos y justificaciones.

## 1) Auditoria y orden de documentacion

### 1.1 Ajustes en indices y README
- **doc/README.md**
  - Se reorganizo el indice para incluir `doc/partes-proyecto.md` y reordenar entradas clave.
  - Se marco documentacion historica como tal para evitar confusiones operativas.
  - Motivo: cumplir las normas de documentacion y mantener un portal claro.
- **README.md**
  - Se corrigieron versiones reales (Next 16.1.1, Node 20.9+).
  - Se ajustaron claims de arquitectura y tests a lo existente.
  - Se removieron comandos de tests inexistentes en frontend.
  - Motivo: evitar alucinaciones y reflejar el estado real del repo.

### 1.2 Correccion de API docs y contratos
- **doc/api/http-api.md**
  - Se alineo con `/v1` y modelos reales (`AskRes`, `QueryReq`, `IngestTextRes`).
  - Se quitaron campos inventados (confidence, query en response).
  - Se documentaron errores reales (`RAGError`, `EmbeddingError`, etc.).
  - Motivo: contratos deben reflejar OpenAPI real y endpoints actuales.

### 1.3 Correccion de schema y queries de DB
- **doc/data/postgres-schema.md**
  - Se alineo a `documents` + `chunks` con UUID y `document_id`.
  - Se actualizaron queries y ejemplos para `document_id`.
  - Motivo: schema real en `infra/postgres/init.sql`.
- **doc/architecture/decisions/003-pgvector-storage.md**
  - Se ajustaron ejemplos a UUID y `document_id`.
  - Motivo: coherencia con schema actual.

### 1.4 Arquitectura, patrones y diagramas
- **doc/architecture/overview.md**
  - Se alinearon interfaces y nombres reales (`find_similar_chunks`, `embed_query`, `generate_answer`).
  - Se actualizo uso de `/v1/ask`.
  - Motivo: reflejar codigo real en capa Clean Architecture.
- **doc/design/patterns.md**
  - Se actualizaron ejemplos a interfaces reales.
  - Se ajusto DI a `container.py` real y no a settings inexistentes.
  - Se eliminaron campos que no existen en entidades reales.
  - Motivo: ejemplos deben ser ejecutables y correctos.
- **doc/design/clean-architecture.md**
  - Se corrigieron ejemplos de entidades y protocolos reales.
  - Se corrigieron endpoints (`/v1/ask`) y DI.
  - Motivo: evitar drift entre docs y codigo.
- **doc/diagrams/sequence-rag-flow.md**
  - Se actualizo flujo a `/v1/ask`.
  - Se ajustaron metodos reales (embed_query/find_similar_chunks/generate_answer).
  - Se removieron respuestas inventadas (confidence, AnswerQueryResponse).
  - Motivo: diagrama debe reflejar flujo actual.
- **doc/diagrams/components.md**
  - Se ajustaron versiones y endpoints.
  - Se marco use cases planned donde no existen.
  - Motivo: diagrama consistente con estado real.
- **doc/diagrams/layers.md**
  - Se actualizaron DTOs, endpoints y ejemplos.
  - Se alinearon protocolos con metodos actuales.
  - Motivo: limpiar inconsistencias con el codigo.

### 1.5 Testing docs
- **doc/quality/testing.md**
  - Se removieron ejemplos falsos y se marco E2E/CI como TODO.
  - Se alineo coverage con `pytest.ini` (70%).
  - Se ajustaron ejemplos a interfaces reales.
  - Motivo: documentar lo que existe y evitar promesas falsas.
- **services/rag-api/tests/README.md**
  - Se corrigieron claims de cobertura y se marco como TODO.
  - Motivo: mantener credibilidad de tests.

### 1.6 Runbook
- **doc/runbook/local-dev.md**
  - Se actualizaron endpoints a `/v1`.
  - Se corrigieron queries a `document_id`.
  - Motivo: evitar comandos rotos en local.

## 2) Frontend (limpieza y modularizacion)

### 2.1 Estructura y UI
- **apps/web/app/page.tsx**
  - Se movio la logica a un hook y se compuso la pagina con componentes.
  - Motivo: legibilidad y mantenimiento.
- **apps/web/app/components/**
  - `PageHeader.tsx`, `QueryForm.tsx`, `StatusBanner.tsx`, `AnswerCard.tsx`, `SourcesList.tsx`.
  - Motivo: separar responsabilidades y facilitar cambios.
- **apps/web/app/hooks/useRagAsk.ts**
  - Centraliza estado, validacion y request hacia `askV1AskPost`.
  - Motivo: encapsular side effects y mantener UI limpia.
- **apps/web/app/globals.css**
  - Se ajusto tipografia base a Geist.
  - Motivo: coherencia visual y evitar fuentes por defecto.
- **apps/web/app/layout.tsx**
  - Metadata actualizada a producto real.
  - Motivo: identidad consistente.

## 3) Backend (migracion a Clean Architecture)

### 3.1 Nuevos casos de uso
- **services/rag-api/app/application/use_cases/ingest_document.py**
  - Orquesta chunk → embed_batch → save_document/save_chunks.
  - Motivo: mover ingesta fuera de rutas legacy.
- **services/rag-api/app/application/use_cases/search_chunks.py**
  - Orquesta embed_query → find_similar_chunks.
  - Motivo: separar retrieval sin LLM.
- **services/rag-api/app/application/use_cases/__init__.py**
  - Exporta nuevos casos de uso.

### 3.2 Contratos y entidades
- **services/rag-api/app/domain/entities.py**
  - Se agrego `similarity` en `Chunk` para devolver score en `/v1/query`.
  - Motivo: endpoints requieren score de similitud.
- **services/rag-api/app/domain/services.py**
  - Se agrego protocolo `TextChunkerService`.
  - Motivo: inyectar estrategia de chunking sin acoplar a funciones.

### 3.3 Infraestructura
- **services/rag-api/app/infrastructure/text/chunker.py**
  - Se creo `SimpleTextChunker` como adaptador.
  - Motivo: inyectable via DI.
- **services/rag-api/app/infrastructure/text/__init__.py**
  - Exporta `SimpleTextChunker`.
- **services/rag-api/app/infrastructure/repositories/postgres_document_repo.py**
  - Se mapea `similarity` desde la query SQL.
  - Motivo: DTOs requieren score.

### 3.4 DI y rutas
- **services/rag-api/app/container.py**
  - Se agrego `get_text_chunker`, `get_ingest_document_use_case`,
    `get_search_chunks_use_case`.
  - Motivo: componer dependencias de nuevos casos de uso.
- **services/rag-api/app/routes.py**
  - `/v1/ingest/text` ahora usa `IngestDocumentUseCase`.
  - `/v1/query` ahora usa `SearchChunksUseCase`.
  - Se elimina dependencia de `Store`, `embeddings.py`, `llm.py` en esos endpoints.
  - Motivo: terminar migracion a Clean Architecture en endpoints legacy.

## 4) Archivos nuevos agregados
- `doc/partes-proyecto.md` (mapa de partes del repo).
- `doc/registro-cambios-chat.md` (este archivo).
- `services/rag-api/app/application/use_cases/ingest_document.py`
- `services/rag-api/app/application/use_cases/search_chunks.py`
- `apps/web/app/hooks/useRagAsk.ts`
- `apps/web/app/components/PageHeader.tsx`
- `apps/web/app/components/QueryForm.tsx`
- `apps/web/app/components/StatusBanner.tsx`
- `apps/web/app/components/AnswerCard.tsx`
- `apps/web/app/components/SourcesList.tsx`

## 5) Criterios aplicados
- Cumplimiento de instrucciones: documentacion sin alucinaciones y con rutas reales.
- Cambios incrementales y con separacion de capas.
- Consistencia entre doc, OpenAPI y codigo real.
- En frontend: modularidad y legibilidad con Tailwind.
- En backend: migracion gradual a Clean Architecture sin refactor masivo.
