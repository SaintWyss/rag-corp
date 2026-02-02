# Parsers (extracción de texto)

## 🎯 Misión
Extraer texto desde archivos (PDF, DOCX, TXT) mediante parsers por MIME, aplicando normalización y límites defensivos.

**Qué SÍ hace**
- Selecciona parser según MIME type.
- Extrae texto y normaliza whitespace.
- Centraliza errores y contratos de parsing.

**Qué NO hace**
- No genera embeddings ni chunking (eso vive en `text/`).
- No persiste nada en DB.

**Analogía (opcional)**
- Es el “lector” que convierte archivos en texto plano.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de parsers y extractor. |
| 🐍 `contracts.py` | Archivo Python | Contratos/DTOs para parsing. |
| 🐍 `document_text_extractor.py` | Archivo Python | Adapter al puerto `DocumentTextExtractor`. |
| 🐍 `docx_parser.py` | Archivo Python | Parser DOCX. |
| 🐍 `errors.py` | Archivo Python | Errores de parsing (MIME no soportado, etc.). |
| 🐍 `mime_types.py` | Archivo Python | Normalización y catálogo de MIME types. |
| 🐍 `normalize.py` | Archivo Python | Normalización/truncado de texto. |
| 🐍 `pdf_parser.py` | Archivo Python | Parser PDF. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `registry.py` | Archivo Python | Registry de parsers por MIME (Strategy). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: bytes del archivo + MIME type.
- **Proceso**: registry elige parser → extrae → normaliza → trunca.
- **Output**: texto plano listo para chunking.

Tecnologías/librerías usadas aquí:
- pypdf, python-docx.

Flujo típico:
- `SimpleDocumentTextExtractor.extract_text()` delega al parser correcto.
- `normalize.py` aplica higiene y límites de tamaño.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (parsing).
- Recibe órdenes de: use cases de ingesta.
- Llama a: parsers concretos y normalizadores.
- Contratos y límites: implementa `DocumentTextExtractor` del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.parsers import SimpleDocumentTextExtractor

extractor = SimpleDocumentTextExtractor()
text = extractor.extract_text("text/plain", b"hola mundo")
```

## 🧩 Cómo extender sin romper nada
- Implementa un parser nuevo que cumpla `BaseParser`.
- Regístralo en `ParserRegistry.register()`.
- Agrega el MIME a `mime_types.py`.
- Actualiza tests de ingesta.

## 🆘 Troubleshooting
- Síntoma: `UnsupportedMimeTypeError` → Causa probable: MIME no registrado → Mirar `registry.py`.
- Síntoma: texto vacío → Causa probable: parser falló → Revisar `pdf_parser.py` o `docx_parser.py`.
- Síntoma: texto truncado → Causa probable: `max_chars` → Mirar `contracts.py`/`normalize.py`.

## 🔎 Ver también
- [Ingestion use cases](../../application/usecases/ingestion/README.md)
- [Text chunking](../text/README.md)
