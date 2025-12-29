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
