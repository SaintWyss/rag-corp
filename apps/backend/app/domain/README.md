# Domain (núcleo del negocio)

## 🎯 Misión
Definir el lenguaje del negocio: entidades, objetos de valor, políticas puras y contratos (puertos) que la aplicación usa para orquestar casos de uso sin depender de infraestructura.

**Qué SÍ hace**
- Modela entidades centrales (Document, Workspace, Chunk, QueryResult, Conversation).
- Define contratos de repositorios y servicios externos (Protocols).
- Provee políticas puras (ej. acceso a workspaces) y normalizadores.

**Qué NO hace**
- No accede a base de datos ni APIs externas.
- No depende de FastAPI, Redis, S3 ni librerías de infraestructura.

**Analogía (opcional)**
- Es el “contrato legal” del negocio: reglas y términos, sin implementación técnica.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | API pública del dominio (re‑exports). |
| 🐍 `access.py` | Archivo Python | Normalización de `allowed_roles` desde metadata. |
| 🐍 `audit.py` | Archivo Python | Modelo de evento de auditoría del dominio. |
| 🐍 `cache.py` | Archivo Python | Puerto de cache de embeddings (Protocol). |
| 🐍 `entities.py` | Archivo Python | Entidades: Document, Workspace, Chunk, QueryResult, Conversation. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `repositories.py` | Archivo Python | Puertos de persistencia (repositorios). |
| 🐍 `services.py` | Archivo Python | Puertos de servicios externos (LLM/embeddings/storage/queue). |
| 🐍 `tags.py` | Archivo Python | Normalización de tags desde metadata. |
| 🐍 `value_objects.py` | Archivo Python | Objetos de valor (sources, quotas, feedback, etc.). |
| 🐍 `workspace_policy.py` | Archivo Python | Policy pura de acceso a workspaces. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: datos del negocio (ej. metadata, roles, visibilidad).
- **Proceso**: normaliza, valida y evalúa políticas sin side‑effects.
- **Output**: entidades/objetos de valor estables y decisiones de acceso.

Tecnologías/librerías usadas aquí:
- Solo Python estándar + typing (sin infraestructura).

Flujo típico:
- Un use case crea `Document` y aplica `normalize_tags`.
- `workspace_policy.can_read_workspace()` decide acceso en base a actor/visibilidad.
- Repositorios y servicios se tipan vía Protocols.

## 🔗 Conexiones y roles
- Rol arquitectónico: Core Domain.
- Recibe órdenes de: capa Application (use cases).
- Llama a: no aplica (solo define contratos/políticas).
- Contratos y límites: no depende de infraestructura ni frameworks.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.domain.entities import Document

doc = Document(id=uuid4(), title="Manual")
doc.mark_deleted()
assert doc.is_deleted
```

## 🧩 Cómo extender sin romper nada
- Agrega nuevas entidades en `entities.py` con invariantes mínimas.
- Si necesitás nuevo puerto, defínelo en `repositories.py` o `services.py`.
- Mantén las políticas puras (sin I/O ni dependencias externas).
- Re‑exporta en `__init__.py` solo lo que sea parte del API del dominio.

## 🆘 Troubleshooting
- Síntoma: imports profundos y acoplamientos → Causa probable: falta export en `__init__.py` → Mirar `domain/__init__.py`.
- Síntoma: policy devuelve False inesperado → Causa probable: actor incompleto → Mirar `workspace_policy.py`.
- Síntoma: roles filtrados vacíos → Causa probable: metadata mal formada → Mirar `access.py`.

## 🔎 Ver también
- [Application](../application/README.md)
- [Identity](../identity/README.md)
- [Infrastructure repos](../infrastructure/repositories/README.md)
