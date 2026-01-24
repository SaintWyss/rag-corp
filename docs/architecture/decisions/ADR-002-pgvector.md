# ADR-002: PostgreSQL + pgvector para búsqueda vectorial

## Estado

**Aceptado** (2024-12)

## Contexto

El sistema RAG requiere almacenamiento de embeddings (768 dimensiones) y búsqueda por similitud coseno eficiente.

Opciones evaluadas:
- Pinecone (SaaS)
- Weaviate (self-hosted)
- Qdrant (self-hosted)
- PostgreSQL + pgvector

## Decisión

Usamos **PostgreSQL 16 + pgvector 0.8.1** como vector store.

### Configuración

```sql
-- Extensión
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de chunks con embedding
CREATE TABLE chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  embedding VECTOR(768) NOT NULL,  -- Google text-embedding-004
  ...
);

-- Índice IVFFlat para búsqueda aproximada
CREATE INDEX chunks_embedding_idx 
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

### Parámetros clave

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| Dimensiones | 768 | Google text-embedding-004 |
| Índice | IVFFlat | Balance precisión/velocidad <10M vectores |
| Lists | 100 | Apropiado para ~100K-1M chunks |

## Consecuencias

### Positivas

- **Simplicidad operativa**: Un solo servicio (PostgreSQL) para datos relacionales y vectores
- **Transacciones ACID**: Consistencia entre documents y chunks
- **Costo**: Sin servicio SaaS adicional
- **Ecosistema**: Herramientas estándar (pg_dump, psql, etc.)

### Negativas

- **Escala**: IVFFlat óptimo hasta ~10M vectores (suficiente para MVP)
- **Latencia**: ~50-100ms para top_k=5 (aceptable)
- **Memoria**: Índice en RAM, requiere tuning para volumen alto

## Migración futura

Si superamos 10M vectores:
1. Migrar a índice HNSW (disponible en pgvector 0.5+)
2. Evaluar Qdrant/Weaviate si latencia crítica

## Referencias

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [infra/postgres/init.sql](../../../infra/postgres/init.sql)
- [IVFFlat vs HNSW](https://github.com/pgvector/pgvector#indexing)
