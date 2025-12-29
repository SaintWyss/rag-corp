#!/bin/bash

echo "🚀 Iniciando migración a Google Gemini..."

# 1. Actualizar dependencias de Python (Agregamos google-generativeai)
cat <<REQ > services/rag-api/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
psycopg[binary]==3.2.1
pgvector==0.3.6
pydantic-settings==2.4.0
httpx==0.27.2
google-generativeai==0.8.3
REQ

# 2. Actualizar Schema de Base de Datos (Cambiamos a 768 dimensiones)
cat <<SQL > infra/postgres/init.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  source TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY,
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(768) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SQL

# 3. Reescribir el Embedder (embeddings.py) para usar Google
cat <<PY > services/rag-api/app/embeddings.py
import os
import google.generativeai as genai
import time

API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Google embedding-004 usa 768 dimensiones
EMBED_DIM = 768

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY no configurada en el entorno")
    
    results = []
    # Procesamos en lotes de a 10 para respetar límites
    for i in range(0, len(texts), 10):
        batch = texts[i:i+10]
        try:
            # Task type retrieval_document es optimizado para guardar en DB
            resp = genai.embed_content(
                model="models/text-embedding-004",
                content=batch,
                task_type="retrieval_document"
            )
            # La respuesta 'embedding' es una lista de listas
            results.extend(resp['embedding'])
        except Exception as e:
            print(f"Error embedding batch: {e}")
            raise e
    return results

def embed_query(query: str) -> list[float]:
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY no configurada")
        
    # Task type retrieval_query es optimizado para buscar
    resp = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    return resp['embedding']
PY

# 4. Actualizar Docker Compose para pasar la clave
cat <<DOCKER > compose.yaml
services:
  db:
    image: pgvector/pgvector:0.8.1-pg16-trixie
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: rag
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/00-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d rag"]
      interval: 5s
      timeout: 5s
      retries: 5

  rag-api:
    build:
      context: ./services/rag-api
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/rag
      # Pasamos la variable del host al contenedor
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    volumes:
      - ./:/repo
    working_dir: /repo/services/rag-api
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
DOCKER

echo "✅ Migración a Gemini configurada correctamente."
