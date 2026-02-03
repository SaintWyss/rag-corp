# Límites del sistema
Fuente de verdad: `apps/backend/app/crosscutting/config.py` (clase `Settings`).

## Límites de request y API
| Límite | Setting | Default | Evidencia |
| :-- | :-- | :-- | :-- |
| Body máximo HTTP | `max_body_bytes` | `10 * 1024 * 1024` | `apps/backend/app/crosscutting/config.py` |
| Upload máximo | `max_upload_bytes` | `25 * 1024 * 1024` | `apps/backend/app/crosscutting/config.py` |
| `top_k` máximo | `max_top_k` | `20` | `apps/backend/app/crosscutting/config.py` |
| Longitud máxima de ingesta | `max_ingest_chars` | `100000` | `apps/backend/app/crosscutting/config.py` |
| Longitud máxima de query | `max_query_chars` | `2000` | `apps/backend/app/crosscutting/config.py` |
| Longitud máxima de título | `max_title_chars` | `200` | `apps/backend/app/crosscutting/config.py` |
| Longitud máxima de source | `max_source_chars` | `500` | `apps/backend/app/crosscutting/config.py` |

## Límites de chunking y contexto
| Límite | Setting | Default | Evidencia |
| :-- | :-- | :-- | :-- |
| Tamaño de chunk | `chunk_size` | `900` | `apps/backend/app/crosscutting/config.py` |
| Overlap de chunk | `chunk_overlap` | `120` | `apps/backend/app/crosscutting/config.py` |
| Contexto máximo | `max_context_chars` | `12000` | `apps/backend/app/crosscutting/config.py` |
| Máx. mensajes por conversación | `max_conversation_messages` | `12` | `apps/backend/app/crosscutting/config.py` |

## Límites de rerank
| Límite | Setting | Default | Evidencia |
| :-- | :-- | :-- | :-- |
| Multiplicador candidatos | `rerank_candidate_multiplier` | `5` | `apps/backend/app/crosscutting/config.py` |
| Máximo de candidatos | `rerank_max_candidates` | `200` | `apps/backend/app/crosscutting/config.py` |
