# Text (chunking)

Como una **máquina cortadora**: toma texto crudo y lo corta en fragmentos estables, con overlap y metadata, para que luego se embeba e indexe.

## 🎯 Misión

Este módulo provee utilidades de **chunking determinístico** usadas durante la ingesta. Convierte texto plano en una lista de chunks (strings) o en fragmentos enriquecidos (`ChunkFragment`) con offsets y metadata mínima.

Su objetivo es que el pipeline de ingesta tenga un paso de fragmentación:

- predecible (mismo input → mismo output),
- defensivo (límites y saneo),
- fácil de testear,
- extensible con variantes (semántico/estructurado) sin romper el baseline.

Recorridos rápidos por intención:

- **Quiero el chunking base (tamaño + overlap, estable)** → `chunker.py` (`chunk_text`, `chunk_fragments`)
- **Quiero fragmentos con offsets y metadatos** → `models.py` (`ChunkFragment`)
- **Quiero heurísticas “semánticas” (cortes por puntuación/pausas)** → `semantic_chunker.py`
- **Quiero respetar estructura (secciones/títulos)** → `structured_chunker.py`
- **Quiero ver cómo se usa en el pipeline de ingesta** → `../../application/usecases/ingestion/process_uploaded_document.py`

### Qué SÍ hace

- Parte texto en chunks con **overlap** configurable.
- Normaliza/sanea texto (mínimo) para evitar chunks vacíos o ruido.
- Expone modelos de fragmentos (`ChunkFragment`) con offsets y campos de metadata básicos.
- Ofrece variantes de chunking:
  - **Semántico:** heurísticas de corte para evitar cortar oraciones en lugares “feos”.
  - **Estructurado:** respeta secciones para mantener contexto por bloque.

### Qué NO hace (y por qué)

- No genera embeddings.
  - **Razón:** embeddings es IO externo (otro subsistema) y se gobierna desde Application.
  - **Impacto:** el output de chunking se pasa al `EmbeddingService` aguas abajo.

- No accede a storage ni DB.
  - **Razón:** este módulo debe ser puro y rápido.
  - **Impacto:** no sabe `document_id` ni guarda resultados; solo devuelve fragmentos.

- No aplica políticas de negocio.
  - **Razón:** permisos/visibilidad se resuelven antes (workspace policy).
  - **Impacto:** no filtra por actor ni workspace; opera sobre texto ya autorizado.

## 🗺️ Mapa del territorio

| Recurso                 | Tipo           | Responsabilidad (en humano)                                                                                   |
| :---------------------- | :------------- | :------------------------------------------------------------------------------------------------------------ |
| `__init__.py`           | Archivo Python | Exporta funciones y modelos de chunking para imports estables.                                                |
| `chunker.py`            | Archivo Python | Chunking base: divide por tamaño y aplica overlap con reglas defensivas (no vacío, merge de cola).            |
| `models.py`             | Archivo Python | Modelo `ChunkFragment`: texto, offsets, índice, longitud y metadata mínima del fragmento.                     |
| `semantic_chunker.py`   | Archivo Python | Chunker con heurísticas semánticas: pre-corte por separadores (puntos, saltos) y luego aplica tamaño/overlap. |
| `structured_chunker.py` | Archivo Python | Chunker estructurado: respeta secciones (títulos/bloques) y produce fragmentos con metadata de sección.       |
| `README.md`             | Documento      | Portada + navegación y contratos del módulo.                                                                  |

## ⚙️ ¿Cómo funciona por dentro?

### Conceptos mínimos (en contexto)

- **Chunk size:** tamaño objetivo del fragmento (caracteres o tokens aproximados, según implementación). Aquí se trabaja sobre texto plano, así que el tamaño es **por caracteres**.
- **Overlap:** solapamiento entre chunks consecutivos para no perder contexto en los bordes. Ej: chunk_size=1000, overlap=200 → cada chunk comparte los últimos 200 caracteres con el siguiente.
- **Offsets:** posiciones (start/end) respecto del texto original para trazabilidad (auditoría, debugging, highlight en UI).

### 1) `chunk_text` (compatibilidad)

**Input**

- `text: str`, `chunk_size: int`, `overlap: int`.

**Proceso**

1. Sanitiza el input:
   - `text.strip()`; si queda vacío → devuelve `[]`.
   - colapsa whitespace extremo (si aplica en helper interno).

2. Valida límites defensivos:
   - `chunk_size` mínimo razonable (ej. > 0).
   - `overlap` se acota a `[0, chunk_size - 1]` (evita loops).

3. Itera sobre ventanas del texto:
   - start = 0
   - end = min(start + chunk_size, len(text))
   - slice = text[start:end]

4. Avanza con overlap:
   - next_start = max(end - overlap, 0)
   - si `next_start` no avanza (por parámetros malos), se corta.

5. Tail merge (si aplica):
   - si el último chunk queda demasiado corto (p. ej. < 30% de `chunk_size`), se mergea al anterior.

**Output**

- `list[str]` con chunks en orden.

### 2) `chunk_fragments` (fragmentos enriquecidos)

**Input**

- `text: str`, `chunk_size`, `overlap`.

**Proceso**

- Reutiliza el mismo algoritmo base, pero en vez de devolver strings:
  - construye `ChunkFragment(index=i, start_offset=start, end_offset=end, text=slice, metadata={...})`.

- Metadata típica:
  - `{"source": "plain", "overlap": overlap, "chunk_size": chunk_size}`.

**Output**

- `list[ChunkFragment]`.

### 3) Chunker semántico (`semantic_chunker.py`)

**Objetivo:** minimizar cortes “antinaturales” (p. ej. partir una oración por la mitad).

**Input**

- texto plano + parámetros de tamaño.

**Proceso**

1. Pre-segmenta por separadores fuertes:
   - saltos de línea dobles, títulos simples, puntos finales, etc.

2. Agrupa segmentos hasta aproximar `chunk_size`.
3. Si un segmento excede `chunk_size`, cae al algoritmo base (split duro) para no romper límites.
4. Aplica overlap entre grupos resultantes.

**Output**

- `list[str]` o `list[ChunkFragment]` (según helper expuesto).

### 4) Chunker estructurado (`structured_chunker.py`)

**Objetivo:** preservar estructura (por ejemplo, secciones) para que el embedding mantenga contexto jerárquico.

**Input**

- texto + heurística de secciones (p. ej. headings, separadores).

**Proceso**

1. Detecta límites de secciones.
2. Para cada sección:
   - genera chunks internos (size/overlap).
   - agrega metadata: `section_title`, `section_index`, `path`.

3. Emite fragmentos con offsets globales (respecto al texto completo) y metadata por sección.

**Output**

- `list[ChunkFragment]` con metadata estructural.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** _Infrastructure_ (text processing puro, sin IO).

- **Recibe órdenes de:**
  - Use cases de ingesta (`application/usecases/ingestion/process_uploaded_document.py`, `ingest_document.py`).

- **Llama a:**
  - Ninguna dependencia externa. Solo Python estándar.

- **Reglas de límites (imports/ownership):**
  - No importa repositorios ni storage.
  - No importa servicios de embeddings/LLM.
  - No conoce `workspace_id` ni permisos.

## 👩‍💻 Guía de uso (Snippets)

### 1) Chunking base (strings)

```python
from app.infrastructure.text.chunker import chunk_text

chunks = chunk_text(
    "Hola mundo. Esto es una prueba.",
    chunk_size=20,
    overlap=5,
)
print(chunks)
```

### 2) Fragmentos con offsets (para trazabilidad)

```python
from app.infrastructure.text.chunker import chunk_fragments

fragments = chunk_fragments(
    "Hola mundo. Esto es una prueba.",
    chunk_size=20,
    overlap=5,
)

for f in fragments:
    print(f.index, f.start_offset, f.end_offset, f.text)
```

### 3) Semántico (mejor cortes por oraciones)

```python
from app.infrastructure.text.semantic_chunker import semantic_chunk_text

chunks = semantic_chunk_text(
    "Linea 1. Linea 2.\n\nTitulo\nContenido largo...",
    chunk_size=500,
    overlap=100,
)
print(len(chunks))
```

### 4) Estructurado (secciones + metadata)

```python
from app.infrastructure.text.structured_chunker import structured_chunk_fragments

fragments = structured_chunk_fragments(
    "# Intro\nTexto...\n\n# Detalles\nMas texto...",
    chunk_size=800,
    overlap=120,
)

for f in fragments:
    print(f.metadata.get("section_title"), f.index)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Mantener baseline estable**
   - `chunk_text` y `chunk_fragments` son el contrato mínimo.
   - Un chunker nuevo no debe cambiar el output del baseline.

2. **Agregar un chunker nuevo**
   - Crear `my_chunker.py`.
   - Exponer una función `my_chunk_text(...)` o `my_chunk_fragments(...)`.
   - Mantener firma compatible: `text`, `chunk_size`, `overlap`, y parámetros opcionales con defaults.

3. **Defensivo por default**
   - Acotar `overlap` para evitar loops (`overlap < chunk_size`).
   - Evitar chunks vacíos.
   - Aplicar tail-merge cuando el último fragmento quede demasiado chico.

4. **Metadata mínima y estable**
   - Si agregás metadata, mantenela chica (evita payloads grandes en DB).
   - No guardes texto duplicado innecesario.

5. **Tests obligatorios**
   - entradas vacías / whitespace.
   - textos muy largos (performance) y parámetros extremos.
   - `chunk_size` pequeño, `overlap` grande.
   - consistencia de offsets (no solaparse mal, end>=start, orden creciente).

## 🆘 Troubleshooting

1. **Se generan demasiados chunks**

- Causa probable: `chunk_size` demasiado bajo o el texto tiene muchos separadores.
- Dónde mirar: parámetros del pipeline (settings de ingesta) y `semantic_chunker.py` (pre-segmentación).
- Solución: subir `chunk_size` o bajar heurísticas de separación.

2. **Chuncks con overlap “infinito” / loop**

- Causa probable: `overlap >= chunk_size`.
- Dónde mirar: validación defensiva en `chunker.py`.
- Solución: acotar `overlap` o fallar fail-fast.

3. **Chunks muy cortos al final**

- Causa probable: tail-merge desactivado o umbral demasiado bajo.
- Dónde mirar: regla de tail-merge en `chunker.py`.
- Solución: activar merge o ajustar el threshold.

4. **Offsets incorrectos (UI resalta mal)**

- Causa probable: normalización de texto previa que cambia longitud sin actualizar offsets.
- Dónde mirar: saneo/normalización en `chunker.py`.
- Solución: si normalizás, hacelo antes y mantené offsets sobre el texto final; o guardá mapping explícito.

5. **Chunker semántico corta “raro”**

- Causa probable: heurística de separadores demasiado agresiva.
- Dónde mirar: lista de separadores y agrupamiento en `semantic_chunker.py`.
- Solución: ajustar separadores, aumentar `chunk_size` o agregar fallback más temprano.

6. **Chunker estructurado pierde títulos**

- Causa probable: el detector de secciones no reconoce el formato (Markdown/HTML).
- Dónde mirar: parsing simple en `structured_chunker.py`.
- Solución: extender detectores (ej. `##`, números, mayúsculas) y agregar tests por formato.

## 🔎 Ver también

- `../../application/usecases/ingestion/README.md` (pipeline de ingesta)
- `../../application/usecases/ingestion/process_uploaded_document.py` (dónde se llama al chunker)
- `../services/README.md` (embeddings y caching, paso siguiente del pipeline)
- `../repositories/postgres/README.md` (persistencia de chunks y búsqueda vectorial)
- `../../domain/services.py` (puertos consumidos por Application: embeddings/LLM)
