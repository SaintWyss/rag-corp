# parsers

Como un **lector**: convierte archivos (PDF/DOCX/TXT) en **texto plano** listo para el pipeline.

## 🎯 Misión

Este módulo implementa la extracción de texto desde archivos a través de **parsers por MIME type** y un extractor unificado que cumple el puerto del dominio (`DocumentTextExtractor`).

Acá se resuelven tres cosas en un solo lugar: **selección de estrategia** (qué parser usar), **normalización defensiva** del texto (whitespace, truncado, límites) y **errores consistentes** para que Application pueda marcar `FAILED` con mensajes claros.

Recorridos rápidos por intención:

- **Quiero ver el punto de entrada (puerto del dominio)** → `document_text_extractor.py`
- **Quiero ver cómo se selecciona el parser (Strategy/Registry)** → `registry.py` (+ `mime_types.py`)
- **Quiero ver cómo se normaliza y limita el texto** → `normalize.py` (+ `contracts.py`)
- **Quiero ver parsers concretos** → `pdf_parser.py` / `docx_parser.py`
- **Quiero entender errores de parsing** → `errors.py`

### Qué SÍ hace

- Selecciona parser según MIME type (registry).
- Extrae texto y aplica normalización (whitespace/higiene) + truncado/límites defensivos.
- Centraliza contratos/DTOs de parsing y errores tipados.
- Implementa el puerto del dominio para que el resto del sistema no conozca librerías (pypdf/python-docx).

### Qué NO hace (y por qué)

- No genera embeddings ni hace chunking.
  - **Razón:** chunking y embeddings viven en el pipeline de texto (y casos de uso de ingesta).
  - **Impacto:** este módulo solo devuelve texto; el tamaño final/fragmentación se decide en `infrastructure/text/`.

- No persiste nada en DB ni marca estados.
  - **Razón:** persistencia/transiciones son responsabilidad de repos y use cases.
  - **Impacto:** ante fallos, este módulo lanza/retorna errores tipados; Application decide `FAILED`.

## 🗺️ Mapa del territorio

| Recurso                      | Tipo           | Responsabilidad (en humano)                                                          |
| :--------------------------- | :------------- | :----------------------------------------------------------------------------------- |
| `__init__.py`                | Archivo Python | Exporta el extractor y componentes públicos (imports estables).                      |
| `contracts.py`               | Archivo Python | DTOs/contratos: opciones de parsing (límites) y resultados normalizados.             |
| `document_text_extractor.py` | Archivo Python | Adaptador que implementa `DocumentTextExtractor` del dominio (entrada unificada).    |
| `docx_parser.py`             | Archivo Python | Parser DOCX (python-docx) con manejo defensivo de errores.                           |
| `errors.py`                  | Archivo Python | Errores tipados: MIME no soportado, parse fallido, archivo corrupto, etc.            |
| `mime_types.py`              | Archivo Python | Catálogo + normalización de MIME types (alias, defaults, comparaciones seguras).     |
| `normalize.py`               | Archivo Python | Normalización y truncado: whitespace, límites de caracteres y protección de memoria. |
| `pdf_parser.py`              | Archivo Python | Parser PDF (pypdf) con extracción página a página y límites.                         |
| `registry.py`                | Archivo Python | Registry/Strategy: mapea MIME → parser y define el fallback/errores.                 |
| `README.md`                  | Documento      | Portada + guía operativa de parsers.                                                 |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output con pasos reales del diseño.

### 1) Entrada unificada: `DocumentTextExtractor`

- **Input:** `mime_type: str` + `content: bytes` (archivo completo) + opciones (si aplica).
- **Proceso:**
  1. `document_text_extractor` normaliza el MIME (`mime_types.normalize_mime_type`).
  2. pide al registry el parser adecuado (`registry.get(mime)`).
  3. ejecuta el parser (PDF/DOCX/TXT) y obtiene texto crudo.
  4. aplica `normalize.normalize_text(...)` (higiene) y `truncate(...)` según límites.

- **Output:** `text: str` listo para chunking.

### 2) Selección de parser (Registry)

- **Input:** MIME type normalizado.
- **Proceso:**
  - El registry mantiene un mapa MIME → `BaseParser`.
  - Si el MIME no está registrado, lanza `UnsupportedMimeTypeError` con el MIME observado.

- **Output:** instancia del parser correcto o error tipado.

### 3) Parsers concretos

- **PDF (`pdf_parser.py`)**
  - extrae texto página a página (para controlar memoria).
  - maneja PDFs sin texto (scans) devolviendo vacío o error (según contrato).

- **DOCX (`docx_parser.py`)**
  - recorre párrafos/celdas y junta texto con separadores estables.
  - ignora objetos no textuales.

- **TXT (si aplica vía registry)**
  - decodifica con fallback (utf-8) y reemplazo controlado.

### 4) Normalización y límites defensivos

- **Whitespace:** colapsa espacios múltiples, normaliza saltos de línea y recorta extremos.
- **Truncado:** aplica un máximo de caracteres (ej. `max_chars`) para evitar OOM y tiempos excesivos.
- **Errores:** se envuelven en errores tipados para que el use case registre `FAILED` con causa clara.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Infrastructure adapter (parsing de archivos).

- **Recibe órdenes de:**
  - Casos de uso de ingesta (ej. `ProcessUploadedDocumentUseCase`) que necesitan texto para chunking.

- **Llama a:**
  - `pypdf` (PDF) y `python-docx` (DOCX), más normalizadores locales.

- **Contratos y límites:**
  - Implementa el puerto `DocumentTextExtractor` definido en `app/domain/services.py`.
  - No debe importar repositorios ni use cases.
  - No decide política ni status; solo devuelve texto o error.

## 👩‍💻 Guía de uso (Snippets)

### 1) Extraer texto directo (runtime)

```python
from app.infrastructure.parsers import SimpleDocumentTextExtractor

extractor = SimpleDocumentTextExtractor()
text = extractor.extract_text("text/plain", b"hola mundo")
print(text)
```

### 2) PDF con MIME normalizado

```python
from app.infrastructure.parsers import SimpleDocumentTextExtractor

extractor = SimpleDocumentTextExtractor()
text = extractor.extract_text("application/pdf", pdf_bytes)
print(text[:200])
```

### 3) Forzar opciones/límites (si `contracts.py` lo expone)

```python
from app.infrastructure.parsers import SimpleDocumentTextExtractor
from app.infrastructure.parsers.contracts import ParseOptions

extractor = SimpleDocumentTextExtractor()
text = extractor.extract_text(
    "application/pdf",
    pdf_bytes,
    options=ParseOptions(max_chars=200_000),
)
```

### 4) Registro de un parser custom (test o extensión)

```python
from app.infrastructure.parsers.registry import ParserRegistry
from app.infrastructure.parsers.contracts import BaseParser

class MarkdownParser(BaseParser):
    def parse(self, content: bytes) -> str:
        return content.decode("utf-8", errors="replace")

registry = ParserRegistry.default()
registry.register("text/markdown", MarkdownParser())
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo parser**: implementá `BaseParser` (contrato en `contracts.py`).
2. **Registro**: agregalo en `registry.py` (o en la construcción default del registry).
3. **MIME**: sumá el MIME/alias en `mime_types.py`.
4. **Normalización**: mantené `normalize.py` como único lugar para whitespace/truncado.
5. **Errores**: lanzá errores tipados de `errors.py` (no `Exception` genérica).
6. **Tests**:
   - unit: parser con archivos pequeños y casos corruptos.
   - integración: flujo de ingesta que use `DocumentTextExtractor`.

## 🆘 Troubleshooting

- **`UnsupportedMimeTypeError`** → MIME no registrado/normalizado → revisar `mime_types.py` y `registry.py` → agregar alias o registrar parser.
- **Texto vacío en PDF** → PDF es imagen (scan) o extractor no encuentra texto → revisar `pdf_parser.py` → considerar OCR (en otro módulo/paso del pipeline).
- **Texto truncado** → `max_chars` bajo → revisar `contracts.py`/`normalize.py` y los settings que inyectan ese límite.
- **`ParseError` / archivo corrupto** → bytes inválidos o contenido incompleto → revisar origen de upload y validar tamaño/hash.
- **DOCX devuelve texto raro** → contenido en tablas/headers no considerado → revisar `docx_parser.py` y el join de párrafos/celdas.

## 🔎 Ver también

- `../../application/usecases/ingestion/README.md` (pipeline: extract → chunk → embed)
- `../text/README.md` (chunking y utilidades de texto)
- `../storage/README.md` (de dónde vienen los bytes: storage ports)
