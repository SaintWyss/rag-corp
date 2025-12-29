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
