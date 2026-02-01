# Infrastructure Parsers Layer

## 🎯 Propósito y Rol

Este paquete (`infrastructure/parsers`) es responsable de **transformar archivos binarios** (PDF, DOCX) en texto plano limpio y normalizado que el sistema RAG pueda consumir.

Implementa un mecanismo robusto de selección de estrategia (Strategy Pattern) basado en tipos MIME, con protecciones contra archivos maliciosos o corruptos.

---

## 🧩 Componentes Principales

### 1. Registry & Factory (El Cerebro)

| Archivo                      | Rol         | Descripción                                                                                         |
| :--------------------------- | :---------- | :-------------------------------------------------------------------------------------------------- |
| `registry.py`                | **Factory** | Mantiene un registro central de `MIME -> Parser`. Permite obtener el parser correcto dinámicamente. |
| `document_text_extractor.py` | **Adapter** | La cara pública hacia el Dominio. Usa el Registry internamente para delegar el trabajo.             |

### 2. Estrategias de Parsing (Los Obreros)

| Archivo                    | Soporte | Descripción                                                                                     |
| :------------------------- | :------ | :---------------------------------------------------------------------------------------------- |
| `pdf_parser.py`            | PDF     | Usa `pypdf`. Maneja extracción página por página, tolerancia a fallos parciales y lazy loading. |
| `docx_parser.py`           | DOCX    | Usa `python-docx`. Extrae párrafos y tablas.                                                    |
| `registry.py` (TextParser) | TXT     | Maneja archivos de texto plano con decodificación resiliente (`utf-8/replace`).                 |

### 3. Seguridad y Estabilidad (Guardrails)

| Archivo         | Rol                 | Descripción                                                                                        |
| :-------------- | :------------------ | :------------------------------------------------------------------------------------------------- |
| `normalize.py`  | **Sanitizer**       | Elimina caracteres nulos, colapsa espacios vacíos y trunca textos excesivamente largos.            |
| `mime_types.py` | **Source of Truth** | Define los MIME types soportados para evitar "drift" entre la API y el Parser.                     |
| `errors.py`     | **Exceptions**      | Define errores tipados (`DocumentParsingError`, `ParsingLimitExceededError`) para manejo granular. |

---

## 🛠️ Patrones de Diseño

### Strategy Pattern

Cada formato de archivo tiene su propia clase (`PdfParser`, `DocxParser`) que implementa la interfaz `BaseParser` (`contracts.py`). Agregar un nuevo formato (ej: Markdown) es tan simple como crear una clase y registrarla, cumpliendo el principio OCP (Open/Closed Principle).

### Lazy Loading

Las librerías pesadas (`pypdf`, `python-docx`) **solo se importan dentro del método parse**.

- **Beneficio:** Inicio rápido de la aplicación (cold start) y menor consumo de memoria si no se procesan esos archivos.

### Adapter Pattern

El dominio solo conoce `DocumentTextExtractor`. Nuestra implementación `SimpleDocumentTextExtractor` adapta esa interfaz simple hacia nuestro sistema complejo de Registry y Parsers.

---

## 🚀 Guía de Uso

```python
# Así lo usa el contenedor de dependencias:
extractor = SimpleDocumentTextExtractor()

# Así se invoca:
text = extractor.extract_text(
    mime_type="application/pdf",
    content=b"%PDF-1.5..."
)
```

### Configuración de Límites

El sistema aplica límites por defecto para protección (Anti-DoS):

- **Max Pages:** 100 (configurable en `ParserOptions`)
- **Max Chars:** 1,000,000 (configurable)
