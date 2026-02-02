# Application (casos de uso y servicios)

## 🎯 Misión
Orquestar la lógica de aplicación: casos de uso, políticas operativas y servicios que coordinan dominio e infraestructura sin depender de HTTP.

**Qué SÍ hace**
- Orquesta casos de uso (chat, documentos, workspaces, ingesta).
- Implementa servicios de aplicación (context builder, reranker, query rewriter).
- Define tareas de seed de desarrollo.

**Qué NO hace**
- No expone endpoints HTTP (eso vive en `app/interfaces`).
- No implementa persistencia concreta (eso vive en `app/infrastructure`).

**Analogía (opcional)**
- Es el “director de orquesta”: coordina músicos (dominio/infra) para lograr el resultado.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | API pública de la capa de aplicación. |
| 🐍 `context_builder.py` | Archivo Python | Ensambla el contexto RAG con fuentes y límites. |
| 🐍 `conversations.py` | Archivo Python | Utilidades de conversaciones (format/ID). |
| 🐍 `dev_seed_admin.py` | Archivo Python | Seed de admin en entornos controlados. |
| 🐍 `dev_seed_demo.py` | Archivo Python | Seed de datos demo (dev/CI). |
| 🐍 `prompt_injection_detector.py` | Archivo Python | Detección y filtrado de prompt injection. |
| 🐍 `query_rewriter.py` | Archivo Python | Reescritura de queries para mejorar retrieval. |
| 🐍 `rate_limiting.py` | Archivo Python | Rate limiting por cuota (ventana deslizante). |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `reranker.py` | Archivo Python | Reranking de chunks por relevancia. |
| 📁 `usecases/` | Carpeta | Casos de uso por bounded context. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: DTOs de entrada desde interfaces o jobs.
- **Proceso**: use cases validan, aplican policy y llaman puertos del dominio.
- **Output**: resultados tipados (Result/Error) para mapear a HTTP o jobs.

Tecnologías/librerías usadas aquí:
- Solo Python estándar + dataclasses/typing (la infraestructura vive afuera).

Flujo típico:
- Un router crea un `*Input` y ejecuta `*UseCase.execute()`.
- El use case usa repositorios/servicios definidos en el dominio.
- Servicios auxiliares (context builder, reranker, rewriter) enriquecen el flujo.

## 🔗 Conexiones y roles
- Rol arquitectónico: Application.
- Recibe órdenes de: Interfaces HTTP y Worker.
- Llama a: Domain (entidades/puertos) e Infrastructure (implementaciones vía container).
- Contratos y límites: Application no importa detalles HTTP ni SQL directo.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.application.context_builder import ContextBuilder
from app.domain.entities import Chunk

builder = ContextBuilder(max_size=2000)
context, used = builder.build([Chunk(content="hola", embedding=[0.0])])
```

## 🧩 Cómo extender sin romper nada
- Crea un nuevo caso de uso en `usecases/` con DTOs de entrada/salida.
- Usa solo puertos del dominio (repos/services), sin infraestructura directa.
- Reexporta el use case en `usecases/__init__.py` si debe ser público.
- Registra el cableado en `app/container.py`.

## 🆘 Troubleshooting
- Síntoma: errores de import al crear use case → Causa probable: export faltante → Mirar `usecases/__init__.py`.
- Síntoma: resultados sin error pero vacíos → Causa probable: dependencias no inyectadas → Mirar `app/container.py`.
- Síntoma: `ContextBuilder` corta el contexto temprano → Causa probable: `max_context_chars` → Mirar `crosscutting/config.py`.

## 🔎 Ver también
- [Use cases](./usecases/README.md)
- [Domain](../domain/README.md)
- [Infrastructure](../infrastructure/README.md)
