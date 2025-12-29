#!/bin/bash

# 1. Crear directorios
mkdir -p apps/web services/rag-api/app services/rag-api/scripts packages/contracts infra/postgres

# 2. Configuración Monorepo
cat <<EOF > pnpm-workspace.yaml
packages:
  - "apps/*"
  - "services/*"
  - "packages/*"
EOF

cat <<EOF > package.json
{
  "name": "rag-corp",
  "private": true,
  "packageManager": "pnpm@10.0.0",
  "scripts": {
    "dev": "turbo run dev --parallel",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "docker:up": "docker compose up -d",
    "docker:down": "docker compose down -v",
    "contracts:export": "docker compose run --rm rag-api python scripts/export_openapi.py --out /repo/packages/contracts/openapi.json",
    "contracts:gen": "pnpm --filter @contracts gen"
  },
  "devDependencies": {
    "turbo": "^2.0.0"
  }
}
EOF

cat <<EOF > turbo.json
{
  "\$schema": "https://turbo.build/schema.json",
  "tasks": {
    "dev": { "cache": false, "persistent": true },
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**", ".next/**"] },
    "lint": { "outputs": [] }
  }
}
EOF

cat <<EOF > .gitignore
node_modules
dist
.next
.env
.venv
__pycache__
*.pyc
.DS_Store
EOF

# 3. Docker Compose e Infra
cat <<EOF > compose.yaml
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
      EMBED_DIM: "1536"
      EMBED_PROVIDER: "dummy"
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
EOF

cat <<EOF > infra/postgres/init.sql
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
  embedding VECTOR(1536) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
EOF

# 4. Servicio Python (RAG API)
cat <<EOF > services/rag-api/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

cat <<EOF > services/rag-api/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
psycopg[binary]==3.2.1
pgvector==0.3.6
pydantic-settings==2.4.0
httpx==0.27.2
EOF

cat <<EOF > services/rag-api/app/main.py
from fastapi import FastAPI
from .routes import router

app = FastAPI(title="RAG Corp API", version="0.1.0")
app.include_router(router, prefix="/v1")

@app.get("/healthz")
def healthz():
    return {"ok": True}
EOF

cat <<EOF > services/rag-api/app/store.py
import os
from uuid import UUID, uuid4
import psycopg
from pgvector.psycopg import register_vector

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag")

class Store:
    def _conn(self):
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        register_vector(conn)
        return conn

    def upsert_document(self, document_id: UUID, title: str, source: str | None, metadata: dict):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, title, source, metadata)
                VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                SET title = EXCLUDED.title,
                    source = EXCLUDED.source,
                    metadata = EXCLUDED.metadata
                """,
                (document_id, title, source, metadata),
            )

    def insert_chunks(self, document_id: UUID, chunks: list[str], vectors: list[list[float]]):
        with self._conn() as conn:
            for idx, (content, emb) in enumerate(zip(chunks, vectors)):
                cid = uuid4()
                conn.execute(
                    """
                    INSERT INTO chunks (id, document_id, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cid, document_id, idx, content, emb),
                )

    def search(self, query_vec: list[float], top_k: int = 5):
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                  id as chunk_id,
                  document_id,
                  content,
                  (1 - (embedding <=> %s)) as score
                FROM chunks
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (query_vec, query_vec, top_k),
            ).fetchall()

        return [
            {"chunk_id": r[0], "document_id": r[1], "content": r[2], "score": r[3]}
            for r in rows
        ]
EOF

cat <<EOF > services/rag-api/app/text.py
def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        j = min(len(text), i + chunk_size)
        chunks.append(text[i:j])
        i = j - overlap
        if i < 0:
            i = 0
        if j == len(text):
            break
    return [c.strip() for c in chunks if c.strip()]
EOF

cat <<EOF > services/rag-api/app/embeddings.py
import os
import hashlib
import math

EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))
PROVIDER = os.getenv("EMBED_PROVIDER", "dummy")

def _dummy_vec(s: str) -> list[float]:
    h = hashlib.sha256(s.encode("utf-8")).digest()
    vals = []
    for i in range(EMBED_DIM):
        b = h[i % len(h)]
        vals.append((b / 255.0) - 0.5)
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [v / norm for v in vals]

def embed_texts(texts: list[str]) -> list[list[float]]:
    return [_dummy_vec(t) for t in texts]

def embed_query(query: str) -> list[float]:
    return _dummy_vec(query)
EOF

cat <<EOF > services/rag-api/app/routes.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from uuid import uuid4, UUID
from .store import Store
from .text import chunk_text
from .embeddings import embed_texts, embed_query

router = APIRouter()
store = Store()

class IngestTextReq(BaseModel):
    title: str
    text: str
    source: str | None = None
    metadata: dict = Field(default_factory=dict)

class IngestTextRes(BaseModel):
    document_id: UUID
    chunks: int

@router.post("/ingest/text", response_model=IngestTextRes)
def ingest_text(req: IngestTextReq):
    doc_id = uuid4()
    chunks = chunk_text(req.text)
    vectors = embed_texts(chunks)

    store.upsert_document(
        document_id=doc_id,
        title=req.title,
        source=req.source,
        metadata=req.metadata,
    )
    store.insert_chunks(doc_id, chunks, vectors)

    return IngestTextRes(document_id=doc_id, chunks=len(chunks))

class QueryReq(BaseModel):
    query: str
    top_k: int = 5

class Match(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float

class QueryRes(BaseModel):
    matches: list[Match]

@router.post("/query", response_model=QueryRes)
def query(req: QueryReq):
    qvec = embed_query(req.query)
    rows = store.search(qvec, top_k=req.top_k)

    matches = [
        Match(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            content=r["content"],
            score=float(r["score"]),
        )
        for r in rows
    ]
    return QueryRes(matches=matches)
EOF

cat <<EOF > services/rag-api/scripts/export_openapi.py
import argparse
import json
from app.main import app

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    schema = app.openapi()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
EOF

# 5. Contracts
cat <<EOF > packages/contracts/package.json
{
  "name": "@contracts",
  "private": true,
  "devDependencies": {
    "orval": "^6.0.0"
  },
  "scripts": {
    "gen": "orval --config orval.config.ts"
  }
}
EOF

cat <<EOF > packages/contracts/orval.config.ts
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
EOF

echo "=== INSTALACION COMPLETA ==="


