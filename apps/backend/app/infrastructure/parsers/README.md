# Infra: Document Parsers

## 🎯 Misión

Extrae texto plano y metadatos desde archivos binarios (`.pdf`, `.docx`, `.txt`).
Es el primer paso para entender un documento subido.

**Qué SÍ hace:**

- Convierte binario -> Texto (Markdown simplificado si es posible).
- Detecta MIME types.

**Qué NO hace:**

- No hace OCR a imágenes (por ahora).

## 🗺️ Mapa del territorio

| Recurso          | Tipo       | Responsabilidad (en humano)                                  |
| :--------------- | :--------- | :----------------------------------------------------------- |
| `contracts.py`   | 🐍 Archivo | Interfaces para los parsers.                                 |
| `docx_parser.py` | 🐍 Archivo | Parser para documentos Word (`python-docx`).                 |
| `pdf_parser.py`  | 🐍 Archivo | Parser para PDFs (`pypdf`).                                  |
| `registry.py`    | 🐍 Archivo | **Factory**. Devuelve el parser adecuado según el MIME type. |
| `normalize.py`   | 🐍 Archivo | Limpieza básica de texto (espacios extra, caracteres raros). |

## ⚙️ ¿Cómo funciona por dentro?

Patrón **Strategy** + **Registry**.

1.  `registry.get_parser("application/pdf")` -> Retorna instancia de `PdfParser`.
2.  `parser.parse(file_stream)` -> Retorna objeto `ParsedDocument`.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapter.
- **Llama a:** Librerías de terceros (`pypdf`, `python-docx`).

## 👩‍💻 Guía de uso (Snippets)

### Parsear un archivo desconocido

```python
parser = ParserRegistry.get(mime_type)
document = parser.parse(file_stream)
print(document.text)
```

## 🧩 Cómo extender sin romper nada

1.  **Soporte HTML:** Crea `html_parser.py` (usando BeautifulSoup), implemanta `DocumentParser` y regístralo en `registry.py`.

## 🆘 Troubleshooting

- **Síntoma:** Texto ilegible o garabatos.
  - **Causa:** El PDF puede ser solo imágenes escaneadas (necesita OCR, no soportado aún).
