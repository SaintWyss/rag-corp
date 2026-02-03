# usecases
Como un **catálogo de operaciones**: cada archivo es una acción completa del sistema.

## 🎯 Misión
Este paquete organiza los casos de uso por bounded context (`chat`, `documents`, `ingestion`, `workspace`). Cada caso de uso valida precondiciones, aplica políticas y coordina puertos del dominio para devolver resultados tipados.

### Qué SÍ hace
- Define Inputs y Results tipados por caso de uso.
- Expone un `execute()` consistente para orquestación.
- Centraliza errores tipados por bounded context (Document/Workspace).
- Publica barrel exports en `usecases/__init__.py`.

### Qué NO hace (y por qué)
- No ejecuta IO directo (DB/Redis/S3/LLM).
  - Razón: el IO se implementa en `infrastructure/`.
  - Consecuencia: los use cases dependen de puertos del dominio.
- No expone endpoints HTTP.
  - Razón: el transporte pertenece a `interfaces/`.
  - Consecuencia: los routers solo adaptan y delegan.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del paquete de casos de uso. |
| `__init__.py` | Archivo Python | Exports públicos de Inputs/UseCases/Results. |
| `chat/` | Carpeta | RAG, conversación y feedback. |
| `documents/` | Carpeta | CRUD de documentos + errores/resultados. |
| `ingestion/` | Carpeta | Upload/processing/ingesta + estado. |
| `workspace/` | Carpeta | Gestión de workspaces + acceso. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** `*Input` (dataclass o similar) con datos mínimos.
- **Proceso:** `UseCase.execute()` valida, aplica policy y usa puertos.
- **Output:** `*Result` con payload o `error` tipado (`DocumentError`, `WorkspaceError`).

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Application (use cases).
- **Recibe órdenes de:** Interfaces HTTP y Worker.
- **Llama a:** puertos del dominio (repos/services) e infraestructura vía inyección.
- **Reglas de límites:** sin FastAPI ni SQL directo.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.application.usecases import SearchChunksInput
from app.container import get_search_chunks_use_case

use_case = get_search_chunks_use_case()
result = use_case.execute(SearchChunksInput(query="q", workspace_id="...", actor=None))
```

```python
from app.application.usecases import UploadDocumentInput
from app.container import get_upload_document_use_case

use_case = get_upload_document_use_case()
use_case.execute(UploadDocumentInput(workspace_id="...", actor=None, title="Doc", file_name="a.pdf", mime_type="application/pdf", content=b"..."))
```

## 🧩 Cómo extender sin romper nada
- Agregá el caso de uso en el bounded context correcto.
- Definí Input/Result tipados y mantené `execute()` como entrada única.
- Si necesitás IO nuevo, agregá el puerto en `domain/` y el adapter en `infrastructure/`.
- Cableá el caso en `app/container.py` y exportalo en `usecases/__init__.py`.
- Tests: unit en `apps/backend/tests/unit/application/`, integration en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `ImportError` al importar desde `app.application.usecases`.
  - **Causa probable:** falta export en `__init__.py`.
  - **Dónde mirar:** `usecases/__init__.py`.
  - **Solución:** exportar el símbolo.
- **Síntoma:** `FORBIDDEN` inesperado.
  - **Causa probable:** actor ausente o sin rol.
  - **Dónde mirar:** `workspace_access.py` en `workspace/`.
  - **Solución:** construir actor válido desde auth.
- **Síntoma:** `VALIDATION_ERROR` por límites.
  - **Causa probable:** `top_k` o inputs fuera de rango.
  - **Dónde mirar:** caso de uso específico.
  - **Solución:** ajustar inputs o límites.
- **Síntoma:** `SERVICE_UNAVAILABLE`.
  - **Causa probable:** dependencia externa no configurada.
  - **Dónde mirar:** `app/container.py` y settings.
  - **Solución:** configurar servicios o habilitar fakes.

## 🔎 Ver también
- `./chat/README.md`
- `./documents/README.md`
- `./ingestion/README.md`
- `./workspace/README.md`
- `../README.md`
