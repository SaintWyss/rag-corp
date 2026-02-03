# application
Como una **sala de mando**: orquesta casos de uso y coordina puertos del dominio.

## 🎯 Misión
La capa Application coordina el comportamiento del sistema: valida precondiciones, aplica políticas y orquesta puertos (repositorios/servicios) para devolver resultados tipados. Acá viven los casos de uso y servicios de aplicación reutilizables.

Rutas rápidas:
- Casos de uso por área → `./usecases/README.md`
- Contexto RAG → `./context_builder.py`
- Rewriter/Reranker → `./query_rewriter.py`, `./reranker.py`
- Rate limiting por cuota → `./rate_limiting.py`
- Seeds de desarrollo → `./dev_seed_admin.py`, `./dev_seed_demo.py`

### Qué SÍ hace
- Define casos de uso con Inputs/Results tipados.
- Aplica políticas operativas (cuotas, filtros, límites).
- Coordina puertos del dominio sin conocer implementaciones concretas.
- Expone servicios de aplicación reutilizables (context builder, rewriter, reranker).

### Qué NO hace (y por qué)
- No define endpoints HTTP ni schemas.
  - Razón: el transporte vive en `interfaces/`.
  - Consecuencia: los casos de uso son invocables desde HTTP o worker.
- No ejecuta SQL ni SDKs externos.
  - Razón: el IO real vive en `infrastructure/`.
  - Consecuencia: las implementaciones se inyectan desde `container.py`.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de la capa Application. |
| `__init__.py` | Archivo Python | Re-exports de servicios de aplicación. |
| `context_builder.py` | Archivo Python | Ensambla contexto RAG con delimitadores y fuentes. |
| `conversations.py` | Archivo Python | Helpers de conversación e historial. |
| `dev_seed_admin.py` | Archivo Python | Seed admin para desarrollo (guardado por settings). |
| `dev_seed_demo.py` | Archivo Python | Seed demo local (usuarios/workspaces). |
| `prompt_injection_detector.py` | Archivo Python | Detector/filtrado de prompt injection (best-effort). |
| `query_rewriter.py` | Archivo Python | Reescritura de queries con LLM (feature flag). |
| `rate_limiting.py` | Archivo Python | Rate limit por cuota (messages/tokens/uploads). |
| `reranker.py` | Archivo Python | Reranking de chunks (heurístico/LLM). |
| `usecases/` | Carpeta | Casos de uso por bounded context. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Contrato común**
  - Input: `*Input` (dataclass o equivalente).
  - Proceso: `UseCase.execute(...)` valida y orquesta puertos.
  - Output: `*Result` con `error` tipado si aplica.
- **Servicios de aplicación**
  - `ContextBuilder` construye contexto con `[S#]` y sección `FUENTES`.
  - `QueryRewriter` mejora consultas con LLM (si está habilitado).
  - `ChunkReranker` reordena candidatos con heurística o LLM.
  - `RateLimiter` controla cuotas por workspace/user.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Application (orquestación + políticas).
- **Recibe órdenes de:** Interfaces HTTP y Worker.
- **Llama a:** puertos del dominio (repositorios/servicios) e infraestructura vía inyección.
- **Reglas de límites:** no importar `interfaces/` ni implementaciones de `infrastructure/`.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.application import ContextBuilder
from app.domain.entities import Chunk

builder = ContextBuilder(max_size=2000)
context, used = builder.build([Chunk(content="...", document_title="Doc", document_id="d1")])
```

```python
from app.application import RateLimitConfig, RateLimiter, InMemoryQuotaStorage

limiter = RateLimiter(InMemoryQuotaStorage(), RateLimitConfig(messages_per_hour=2))
check = limiter.check("messages", workspace_id="...")
```

```python
from app.container import get_answer_query_use_case
use_case = get_answer_query_use_case()
```

## 🧩 Cómo extender sin romper nada
- Si agregás un caso de uso, definilo en `usecases/` y exportalo en `__init__.py` correspondiente.
- Si necesitás IO nuevo, definí un puerto en `domain/` y un adapter en `infrastructure/`.
- Cableá la implementación en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/application/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `ValueError` por recursos de rate limit.
  - **Causa probable:** resource no reconocido.
  - **Dónde mirar:** `rate_limiting.py`.
  - **Solución:** usar nombres permitidos o extender config.
- **Síntoma:** `QueryRewriter` no actúa.
  - **Causa probable:** feature flag deshabilitado o query no cumple criterios.
  - **Dónde mirar:** `query_rewriter.py` y settings.
  - **Solución:** habilitar flag y validar precondiciones.
- **Síntoma:** contexto RAG vacío.
  - **Causa probable:** `max_size` bajo o chunks vacíos.
  - **Dónde mirar:** `context_builder.py`.
  - **Solución:** ajustar límites y revisar chunks.
- **Síntoma:** import de use case falla.
  - **Causa probable:** falta re-export en `usecases/__init__.py`.
  - **Dónde mirar:** `usecases/__init__.py`.
  - **Solución:** exportar el símbolo.

## 🔎 Ver también
- `./usecases/README.md`
- `../domain/README.md`
- `../infrastructure/README.md`
- `../container.py`
