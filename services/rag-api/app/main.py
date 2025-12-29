from fastapi import FastAPI
from .routes import router

app = FastAPI(title="RAG Corp API", version="0.1.0")
app.include_router(router, prefix="/v1")

@app.get("/healthz")
def healthz():
    return {"ok": True}
