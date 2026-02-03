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

- No genera embeddings. Razón: ** embeddings es IO externo (otro subsistema) y se gobierna desde Application. Impacto: ** el output de chunking se pasa al `EmbeddingService` aguas abajo.

- No accede a storage ni DB. Razón: ** este módulo debe ser puro y rápido. Impacto: ** no sabe `document_id` ni guarda resultados; solo devuelve fragmentos.

- No aplica políticas de negocio. Razón: ** permisos/visibilidad se resuelven antes (workspace policy). Impacto: ** no filtra por actor ni workspace; opera sobre texto ya autorizado.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :---------------------- | :------------- | :------------------------------------------------------------------------------------------------------------ |
| `__init__.py` | Archivo Python | Exporta funciones y modelos de chunking para imports estables. |
| `chunker.py` | Archivo Python | Chunking base: divide por tamaño y aplica overlap con reglas defensivas (no vacío, merge de cola). |
| `models.py` | Archivo Python | Modelo `ChunkFragment`: texto, offsets, índice, longitud y metadata mínima del fragmento. |
| `semantic_chunker.py` | Archivo Python | Chunker con heurísticas semánticas: pre-corte por separadores (puntos, saltos) y luego aplica tamaño/overlap. |
| `structured_chunker.py` | Archivo Python | Chunker estructurado: respeta secciones (títulos/bloques) y produce fragmentos con metadata de sección. |
| `README.md` | Documento | Portada + navegación y contratos del módulo. |

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
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.infrastructure.text.chunker import chunk_text

chunks = chunk_text("Hola mundo. Esto es una prueba.", chunk_size=20, overlap=5)
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.infrastructure.text.chunker import chunk_fragments

fragments = chunk_fragments("Hola mundo...", chunk_size=50, overlap=10)
for f in fragments:
    print(f.index, f.start, f.end)
```

```python
# Por qué: deja visible el flujo principal.
from app.infrastructure.text.semantic_chunker import semantic_chunk_text

chunks = semantic_chunk_text("Linea 1. Linea 2.", chunk_size=500, overlap=100)
```

## 🧩 Cómo extender sin romper nada
- Mantener `chunk_text` y `chunk_fragments` como contrato base.
- Si agregás un chunker nuevo, mantené firma compatible.
- Cableá el chunker en `app/container.py` si se usa en runtime.
- Tests: unit en `apps/backend/tests/unit/infrastructure/`.

## 🆘 Troubleshooting
- **Síntoma:** demasiados chunks.
- **Causa probable:** `chunk_size` bajo.
- **Dónde mirar:** settings de ingesta.
- **Solución:** aumentar `chunk_size`.
- **Síntoma:** overlap infinito/loop.
- **Causa probable:** `overlap >= chunk_size`.
- **Dónde mirar:** `chunker.py`.
- **Solución:** ajustar parámetros.
- **Síntoma:** offsets incorrectos.
- **Causa probable:** normalización previa mal aplicada.
- **Dónde mirar:** `chunker.py`.
- **Solución:** normalizar antes y mantener offsets consistentes.
- **Síntoma:** chunker estructurado pierde títulos.
- **Causa probable:** detector de secciones insuficiente.
- **Dónde mirar:** `structured_chunker.py`.
- **Solución:** ajustar heurísticas.

## 🔎 Ver también
- `../../application/usecases/ingestion/README.md`
- `../services/README.md`
- `../repositories/README.md`
