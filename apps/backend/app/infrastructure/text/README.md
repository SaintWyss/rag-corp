# Text (chunking)

## 🎯 Misión
Proveer utilidades de chunking de texto para la ingesta: fragmentación determinística, modelos de fragmentos y variantes semánticas/estructuradas.

**Qué SÍ hace**
- Parte texto en chunks con overlap y metadata básica.
- Ofrece modelos de fragmentos (`ChunkFragment`).
- Expone chunkers semánticos/estructurados.

**Qué NO hace**
- No genera embeddings ni accede a storage.
- No aplica políticas de negocio.

**Analogía (opcional)**
- Es la “máquina cortadora” que prepara texto para indexarlo.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de chunking. |
| 🐍 `chunker.py` | Archivo Python | Chunking base con overlap. |
| 🐍 `models.py` | Archivo Python | Modelo `ChunkFragment`. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `semantic_chunker.py` | Archivo Python | Chunking con heurísticas semánticas. |
| 🐍 `structured_chunker.py` | Archivo Python | Chunking respetando estructura (secciones). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: texto plano.
- **Proceso**: separadores, overlap y límites de chunks.
- **Output**: lista de strings o `ChunkFragment` con metadata.

Tecnologías/librerías usadas aquí:
- Python estándar.

Flujo típico:
- `chunk_fragments()` construye fragmentos con offsets.
- `chunk_text()` devuelve solo strings (compatibilidad).
- Chunkers semánticos/estructurados aplican heurísticas adicionales.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (text processing).
- Recibe órdenes de: use cases de ingesta.
- Llama a: ninguna dependencia externa.
- Contratos y límites: output alimenta embeddings y repos.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.text.chunker import chunk_text

chunks = chunk_text("Hola mundo. Esto es una prueba.", chunk_size=20, overlap=5)
```

## 🧩 Cómo extender sin romper nada
- Si agregas un nuevo chunker, mantené `chunk_text` como baseline.
- Respetá límites de tamaño y overlap defensivos.
- Agrega tests para entradas largas y edge cases.

## 🆘 Troubleshooting
- Síntoma: demasiados chunks → Causa probable: `chunk_size` bajo → Ajustar settings.
- Síntoma: chunks muy cortos al final → Causa probable: tail merge desactivado → Revisar `chunker.py`.

## 🔎 Ver también
- [Ingestion use cases](../../application/usecases/ingestion/README.md)
- [Domain services](../../domain/services.py)
