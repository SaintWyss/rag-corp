# Use Cases (Business Operations)

Esta carpeta contiene los **Casos de Uso** de la aplicación. Cada caso de uso representa una **acción de negocio completa** que un usuario (humano o sistema) puede ejecutar.

## Estructura por Feature

```
usecases/
├── chat/              # Interacción conversacional RAG
│   ├── answer_query.py      # Chat Q&A con contexto
│   └── search_chunks.py     # Búsqueda semántica pura
│
├── ingestion/         # Pipeline de documentos
│   ├── ingest_document.py   # Orquestar: parse → chunk → embed → store
│   ├── upload_document.py   # Subir archivo a storage
│   ├── process_uploaded_document.py  # Worker async
│   └── reprocess_document.py  # Re-embedear un doc existente
│
├── documents/         # CRUD de documentos
│   ├── get_document.py      # Obtener por ID
│   ├── list_documents.py    # Listar por workspace
│   ├── delete_document.py   # Eliminar doc + chunks
│   └── document_results.py  # DTOs de respuesta
│
└── workspace/         # Gestión de espacios de trabajo
    ├── create_workspace.py  # Crear nuevo
    ├── get_workspace.py     # Obtener por ID
    ├── list_workspaces.py   # Listar (owner/shared)
    ├── update_workspace.py  # Actualizar metadata
    ├── archive_workspace.py # Soft-delete
    ├── publish_workspace.py # Cambiar visibilidad
    ├── share_workspace.py   # Compartir con usuarios
    ├── workspace_access.py  # Verificar permisos
    └── workspace_results.py # DTOs de respuesta
```

## Flujo de Trabajo (Pipelines)

### 1. Ingestion Pipeline

```
Usuario sube PDF
       ↓
  upload_document.py
       ↓ (guarda en storage, crea registro pending)
  process_uploaded_document.py (Worker/Queue)
       ↓
  ingest_document.py
       ↓ (parse → chunk → embed)
  Chunks guardados en Vector DB
```

### 2. Chat Pipeline

```
Usuario pregunta
       ↓
  answer_query.py
       ↓
  rag_retrieval (embed query → search → build context)
       ↓
  LLMService.generate_answer
       ↓
  Respuesta con citas [S#]
```

## Principios

1.  **Un Use Case = Una Acción:** Cada archivo hace UNA cosa bien. No hay monstruos de 500 líneas.
2.  **Orquestación, no Implementación:** Los use cases llaman a servicios/repos, no hacen SQL ni HTTP directamente.
3.  **DTOs Explícitos:** Los `*_results.py` definen las estructuras de retorno para evitar diccionarios mágicos.
4.  **Fail-Fast:** Validaciones al inicio del use case (workspace existe, usuario tiene permiso).

## Cómo agregar un nuevo Use Case

1.  Decide a qué feature pertenece (chat, ingestion, documents, workspace).
2.  Crea el archivo `{verbo}_{sustantivo}.py` en esa carpeta.
3.  Exporta la función/clase principal en el `__init__.py` de la subcarpeta.
4.  Añádelo al `__all__` del `__init__.py` raíz de usecases.

---

**Nota:** Los use cases dependen de los helpers de `application/` (como `rag_retrieval`, `context_builder`) y de los puertos del `domain/` (repositorios, servicios). Nunca importan directamente de `infrastructure/`.
