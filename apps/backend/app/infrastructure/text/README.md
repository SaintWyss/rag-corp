# Infrastructure Text Layer

## 🎯 Propósito y Rol

Este paquete (`infrastructure/text`) se encarga de **procesar y dividir texto** (Chunking).
Es una etapa crítica para RAG: un mal chunking rompe el contexto semántico y confunde al LLM.

---

## 🧩 Componentes Principales

| Archivo                 | Rol          | Descripción                                                                                                                |
| :---------------------- | :----------- | :------------------------------------------------------------------------------------------------------------------------- |
| `chunker.py`            | **Core**     | Algoritmo de chunking recursivo. Prioriza cortes naturales (`\n\n`, `\n`, `.`). Expone la función compatible `chunk_text`. |
| `structured_chunker.py` | **Strategy** | Chunking consciente de Markdown. Respeta bloques de código (```), headers (#) y listas. Evita romper sintaxis.             |
| `models.py`             | **DTO**      | Define `ChunkFragment`, un objeto rico con metadatos (índice, contexto previo/siguiente, sección).                         |

---

## 🛠️ Modos de Funcionamiento

El sistema soporta dos modos, configurables vía variable de entorno `TEXT_CHUNKER_MODE`:

### 1. `simple` (Default)

Técnica: "Recursive Character Splitting".

- **Ventaja**: Rápido, predecible, funciona con cualquier texto sucio.
- **Desventaja**: Puede partir una tabla o un bloque de código python a la mitad.

### 2. `structured` (Recomendado para Docs Técnicos)

Técnica: "Structure Aware Splitting".

- Analiza Markdown headers.
- Protege bloques de código y tablas.
- Agrupa párrafos bajo su sección correspondiente.

---

## 🚀 Guía de Uso

```python
# Uso vía Container (transparente)
chunker = get_text_chunker()
chunks = chunker.chunk("Texto largo...")

# Uso directo (Chunking Rico)
from app.infrastructure.text.chunker import chunk_fragments

fragments = chunk_fragments("Texto...", chunk_size=500)
for frag in fragments:
    print(f"Index: {frag.index}, Section: {frag.section}")
```
