# Repositories In‑Memory

## 🎯 Misión
Proveer implementaciones en memoria de repositorios para tests y entornos de desarrollo.

**Qué SÍ hace**
- Implementa repositorios de conversación, workspace y feedback en memoria.
- Permite tests rápidos sin DB.
- Mantiene contratos del dominio.

**Qué NO hace**
- No persiste datos entre procesos.
- No reemplaza los repositorios Postgres en producción.

**Analogía (opcional)**
- Es una “libreta temporal” que se borra al apagar el proceso.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de repositorios in‑memory. |
| 🐍 `audit_repository.py` | Archivo Python | Auditoría en memoria (para tests). |
| 🐍 `conversation.py` | Archivo Python | Historial de conversación en memoria. |
| 🐍 `feedback_repository.py` | Archivo Python | Votos/feedback en memoria. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `workspace.py` | Archivo Python | Workspaces en memoria. |
| 🐍 `workspace_acl.py` | Archivo Python | ACL de workspace en memoria. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: llamadas desde casos de uso o tests.
- **Proceso**: estructuras Python (dict/deque/list) con locks si aplica.
- **Output**: entidades o colecciones de dominio.

Tecnologías/librerías usadas aquí:
- Python estándar (collections, threading).

Flujo típico:
- `InMemoryConversationRepository` guarda mensajes en `deque`.
- `InMemoryWorkspaceRepository` mantiene workspaces en dict.
- `InMemoryWorkspaceAclRepository` maneja miembros compartidos.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (testing/dev).
- Recibe órdenes de: Application (use cases) en modo test.
- Llama a: ninguna dependencia externa.
- Contratos y límites: comportamiento efímero, sin persistencia real.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.infrastructure.repositories.in_memory import InMemoryConversationRepository

repo = InMemoryConversationRepository(max_messages=10)
```

## 🧩 Cómo extender sin romper nada
- Mantén la misma firma que el protocolo del dominio.
- Asegura thread‑safety si se usa en tests concurrentes.
- Evita side‑effects globales; inicializa estado en `__init__`.

## 🆘 Troubleshooting
- Síntoma: conversaciones se pierden → Causa probable: repo reiniciado → Esperable en in‑memory.
- Síntoma: comportamiento distinto a Postgres → Causa probable: falta de paridad en reglas → Revisa contratos.

## 🔎 Ver también
- [Repositories](../README.md)
- [Domain repositories](../../../domain/repositories.py)
