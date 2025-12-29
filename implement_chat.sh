#!/bin/bash

echo "🤖 Agregando capacidad de habla (Generación)..."

# 1. Crear módulo LLM (El cerebro que habla)
cat <<PY > services/rag-api/app/llm.py
import os
import google.generativeai as genai

# Usamos la misma clave que ya configuramos
API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def generate_rag_answer(query: str, context_chunks: list[str]) -> str:
    if not API_KEY:
        return "Error: API Key no configurada."

    # Unimos los fragmentos encontrados en un solo texto
    context_text = "\n\n".join(context_chunks)
    
    # El Prompt: La instrucción maestra para la IA
    prompt = f"""
    Actúa como un asistente experto de la empresa RAG Corp.
    Tu misión es responder la pregunta del usuario basándote EXCLUSIVAMENTE en el contexto proporcionado abajo.
    
    Reglas:
    1. Si la respuesta no está en el contexto, decí "No tengo información suficiente en mis documentos".
    2. Sé conciso y profesional.
    3. Respondé siempre en español.

    --- CONTEXTO ---
    {context_text}
    ----------------
    
    Pregunta: {query}
    Respuesta:
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generando respuesta: {str(e)}"
PY

# 2. Actualizar Rutas para incluir el endpoint /ask
cat <<PY > services/rag-api/app/routes.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from uuid import uuid4, UUID
from .store import Store
from .text import chunk_text
from .embeddings import embed_texts, embed_query
from .llm import generate_rag_answer # <-- Importamos el nuevo cerebro

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

# --- NUEVO ENDPOINT: RAG COMPLETO ---
class AskRes(BaseModel):
    answer: str
    sources: list[str]

@router.post("/ask", response_model=AskRes)
def ask(req: QueryReq):
    # 1. Recuperar (Retrieval)
    qvec = embed_query(req.query)
    # Buscamos los 3 fragmentos más relevantes
    rows = store.search(qvec, top_k=3)
    
    context = [r["content"] for r in rows]
    
    # 2. Generar (Generation)
    if not context:
        answer = "No encontré documentos relacionados a tu pregunta."
    else:
        answer = generate_rag_answer(req.query, context)
        
    return AskRes(answer=answer, sources=context)
PY

echo "✅ Backend actualizado con Chat."
