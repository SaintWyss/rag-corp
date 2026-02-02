# Use Cases (casos de uso)

## 🎯 Misión
Organizar los casos de uso por bounded context (chat, documentos, ingesta, workspace), con DTOs de entrada/salida y errores tipados.

**Qué SÍ hace**
- Define DTOs de entrada (`*Input`) y resultados (`*Result`).
- Orquesta flujos de negocio sin depender de HTTP.
- Expone un API público vía `usecases/__init__.py`.

**Qué NO hace**
- No implementa acceso a DB/LLMs directamente.
- No define endpoints ni validaciones de request HTTP.

**Analogía (opcional)**
- Es el “menú” de operaciones de negocio disponibles en el backend.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Barrel exports de casos de uso y DTOs. |
| 📁 `chat/` | Carpeta | RAG, búsqueda y conversación. |
| 📁 `documents/` | Carpeta | CRUD de documentos y resultados comunes. |
| 📁 `ingestion/` | Carpeta | Upload, procesamiento y re‑ingesta. |
| 📄 `README.md` | Documento | Esta documentación. |
| 📁 `workspace/` | Carpeta | Gestión y acceso a workspaces. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: DTOs `*Input` con datos validados por la capa HTTP.
- **Proceso**: use case aplica políticas, llama repos/services y coordina pasos.
- **Output**: `*Result` con `error` tipado o payload de éxito.

Tecnologías/librerías usadas aquí:
- dataclasses/typing (sin dependencias externas).

Flujo típico:
- Router construye `*Input`.
- `*UseCase.execute()` decide y delega en puertos del dominio.
- El resultado se mapea a HTTP (RFC7807) en interfaces.

## 🔗 Conexiones y roles
- Rol arquitectónico: Application (Use Cases).
- Recibe órdenes de: Interfaces HTTP y Worker.
- Llama a: Domain (repos/services) y Application helpers.
- Contratos y límites: sin infraestructura directa, sin FastAPI.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.application.usecases import SearchChunksInput
from app.container import get_search_chunks_use_case

use_case = get_search_chunks_use_case()
result = use_case.execute(
    SearchChunksInput(query="hola", workspace_id=uuid4(), actor=None)
)
```

## 🧩 Cómo extender sin romper nada
- Crea un nuevo módulo en el subpaquete correcto (chat/documents/ingestion/workspace).
- Define `*Input` y `*Result` con errores tipados.
- Mantén dependencias solo a puertos del dominio.
- Exporta el caso de uso en `usecases/__init__.py` si se consume desde fuera.
- Cablea en `app/container.py` y agrega tests.

## 🆘 Troubleshooting
- Síntoma: `ImportError` desde `usecases` → Causa probable: falta export en `__init__.py` → Mirar `usecases/__init__.py`.
- Síntoma: `error` siempre `None` pero resultado vacío → Causa probable: dependencia None → Mirar `app/container.py`.
- Síntoma: `FORBIDDEN` inesperado → Causa probable: actor/policy → Mirar `workspace_policy.py`.

## 🔎 Ver también
- [Chat](./chat/README.md)
- [Documents](./documents/README.md)
- [Ingestion](./ingestion/README.md)
- [Workspace](./workspace/README.md)
