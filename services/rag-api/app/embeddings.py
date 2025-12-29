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
