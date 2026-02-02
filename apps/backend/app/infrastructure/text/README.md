# Infra: Text Processing (Chunking)

## 🎯 Misión

Se encarga de dividir textos largos en fragmentos más pequeños (**Chunks**) para que quepan en la ventana de contexto del LLM y para facilitar la búsqueda semántica.
Es una parte crítica del pipeline RAG.

**Qué SÍ hace:**

- Implementa estrategias de chunking: Estructurado (Markdown) y Semántico.
- Calcula estadísticas básicas de texto.

**Qué NO hace:**

- No genera embeddings (eso es `services`).

## 🗺️ Mapa del territorio

| Recurso                 | Tipo       | Responsabilidad (en humano)                                                         |
| :---------------------- | :--------- | :---------------------------------------------------------------------------------- |
| `chunker.py`            | 🐍 Archivo | Interfaz base para todos los chunkers.                                              |
| `models.py`             | 🐍 Archivo | Modelos de datos para representar un Chunk de texto.                                |
| `semantic_chunker.py`   | 🐍 Archivo | **Avanzado**. Divide texto basándose en cambios de significado (usando embeddings). |
| `structured_chunker.py` | 🐍 Archivo | **Heurístico**. Divide texto respetando encabezados Markdown (#, ##).               |

## ⚙️ ¿Cómo funciona por dentro?

### Structured Chunker

Intenta mantener juntos los párrafos bajo un mismo título.
Si un bloque es muy grande, lo divide recursivamente.

### Semantic Chunker

Calcula embeddings de oraciones consecutivas. Si la similitud ("distancia coseno") cae drásticamente entre la oración A y B, inserta un corte, asumiendo cambio de tema.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure / Domain Service Implementation.
- **Usado por:** `IngestDocumentUseCase`.

## 👩‍💻 Guía de uso (Snippets)

### Chunking Estructurado

```python
chunker = StructuredChunker(max_tokens=500)
chunks = chunker.chunk(text="# Titulo\nContenido...")
# chunks es list[TextChunk]
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevo Algoritmo:** Hereda de `Chunker` y define `chunk()`.
2.  **Configuración:** Los parámetros (max_tokens, overlap) deberían venir inyectados.

## 🔎 Ver también

- [Ingesta de Documentos (Consumidor)](../../../application/usecases/ingestion/README.md)
