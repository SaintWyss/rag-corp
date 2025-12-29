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
