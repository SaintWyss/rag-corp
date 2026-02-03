# domain

El **contrato legal del negocio**: define reglas, términos y decisiones, sin implementar base de datos, colas ni frameworks.

## 🎯 Misión

Este módulo define el **lenguaje del negocio** del backend: entidades, objetos de valor, políticas puras y contratos (puertos) que el resto del sistema usa para construir features sin acoplarse a infraestructura.

Recorridos rápidos por intención:

- **Quiero entender los conceptos centrales (Document/Workspace/Chunk/Conversation)** → `entities.py`
- **Quiero ver decisiones de acceso (quién puede ver qué)** → `workspace_policy.py`
- **Quiero ver contratos de persistencia** → `repositories.py`
- **Quiero ver contratos de servicios externos (LLM/embeddings/storage/queue)** → `services.py`
- **Quiero ver normalizadores de metadata** → `access.py` (roles) / `tags.py` (tags)
- **Quiero ver el modelo de auditoría** → `audit.py`
- **Quiero ver objetos de valor (tipos estables)** → `value_objects.py`

### Qué SÍ hace

- Modela entidades centrales del sistema (ej. `Document`, `Workspace`, `Chunk`, `QueryResult`, `Conversation`).
- Define **contratos** (Protocols) para repositorios y servicios externos que Application/Infrastructure implementan.
- Provee políticas puras y normalizadores que transforman entrada “sucia” (metadata) en datos consistentes.
- Expone una API pública estable del dominio mediante re-exports en `__init__.py`.

### Qué NO hace (y por qué)

- No accede a base de datos, colas, storage ni APIs externas.
  - **Razón:** el dominio no puede depender de detalles de IO.
  - **Impacto:** cualquier función que necesite IO va en Infrastructure o Application; acá solo se tipa el contrato.

- No depende de FastAPI, Redis, S3 ni librerías de infraestructura.
  - **Razón:** mantener el núcleo portable y testeable con unit tests puros.
  - **Impacto:** los modelos y políticas se pueden usar igual en worker, HTTP o scripts.

## 🗺️ Mapa del territorio

| Recurso               | Tipo           | Responsabilidad (en humano)                                                                      |
| :-------------------- | :------------- | :----------------------------------------------------------------------------------------------- |
| `__init__.py`         | Archivo Python | API pública del dominio (re-exports) para imports estables y poco acoplamiento.                  |
| `access.py`           | Archivo Python | Normaliza `allowed_roles` desde metadata (entrada libre → lista válida/estable).                 |
| `audit.py`            | Archivo Python | Modelo de evento de auditoría del dominio (qué pasó, quién, cuándo, con qué payload acotado).    |
| `cache.py`            | Archivo Python | Puerto de cache de embeddings (Protocol) para evitar recomputar y controlar TTL.                 |
| `entities.py`         | Archivo Python | Entidades del dominio (estado y comportamientos con invariantes).                                |
| `repositories.py`     | Archivo Python | Puertos de persistencia (repositorios) para workspaces, documentos, chunks, conversaciones, etc. |
| `services.py`         | Archivo Python | Puertos de servicios externos: LLM/embeddings/storage/queue/extractores.                         |
| `tags.py`             | Archivo Python | Normalización de tags desde metadata (limpia, deduplica, limita y ordena).                       |
| `value_objects.py`    | Archivo Python | Objetos de valor (tipos pequeños e inmutables): sources, quotas, feedback, etc.                  |
| `workspace_policy.py` | Archivo Python | Policy pura de acceso a workspaces (read/write/share) basada en actor + visibilidad.             |
| `README.md`           | Documento      | Portada + índice del dominio y sus reglas de límites.                                            |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output. Acá no hay side-effects: solo decisiones, normalización y contratos.

### 1) Normalización de metadata (roles/tags)

- **Input:** `metadata` (diccionarios con valores libres provenientes de UI/imports).
- **Proceso:**
  - `access.py`: interpreta `allowed_roles` de forma tolerante (tipos mixtos, mayúsculas/minúsculas, vacíos) y devuelve una lista válida.
  - `tags.py`: limpia tags (espacios, duplicados, caracteres) y devuelve una lista lista para persistencia/búsqueda.

- **Output:** listas normalizadas que los casos de uso pueden guardar sin propagar basura.

### 2) Políticas puras de acceso (workspace_policy)

- **Input:** `WorkspaceActor` + atributos del workspace (ej. visibilidad/estado) + ACL asociada.
- **Proceso:** funciones puras que responden “permitido / no permitido” sin leer DB ni mirar request HTTP.
- **Output:** decisión de acceso que Application usa para cortar rápido (fail-fast) o filtrar listados.

### 3) Entidades y objetos de valor

- **Input:** datos del negocio (ids, títulos, estados, relaciones).
- **Proceso:**
  - Entidades encapsulan estado y operaciones coherentes (invariantes del agregado).
  - Objetos de valor representan conceptos pequeños que se comparan por valor.

- **Output:** estructuras estables que Application persiste o expone, y que Interfaces serializa.

### 4) Puertos (Protocols)

- **Input:** necesidades del sistema (persistir, buscar, embebder, almacenar archivos, encolar jobs).
- **Proceso:** `repositories.py`/`services.py` definen interfaces (Protocols) que describen capacidades sin elegir tecnología.
- **Output:** contratos que Infrastructure implementa y el Container inyecta en los casos de uso.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Core Domain.

- **Recibe órdenes de:**
  - _Application_ (use cases), que invoca entidades/policies/normalizadores y opera a través de puertos.

- **Llama a:**
  - No aplica: el dominio no ejecuta IO ni depende de servicios concretos.

- **Reglas de límites (imports/ownership):**
  - `app/domain/**` no importa `app/infrastructure/**` ni `app/interfaces/**`.
  - Se permite `typing`/`dataclasses`/stdlib.
  - Protocols son la frontera: Application depende de Protocols; Infrastructure implementa Protocols.
  - `__init__.py` expone una superficie de imports corta: evita imports profundos repetidos.

## 👩‍💻 Guía de uso (Snippets)

### 1) Entidades: operar sin IO

```python
from uuid import uuid4

from app.domain.entities import Document

doc = Document(id=uuid4(), title="Manual")
doc.mark_deleted()
assert doc.is_deleted
```

### 2) Políticas: decisión de lectura/escritura (sin HTTP)

```python
from uuid import UUID

from app.domain.workspace_policy import WorkspaceActor, can_read_workspace
from app.identity.users import UserRole

actor = WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.EMPLOYEE)

# workspace/acl se obtienen por repositorios en Application; acá solo se evalúa.
allowed = can_read_workspace(actor=actor, workspace_visibility="private", actor_has_acl=False)
print(allowed)
```

### 3) Normalización: roles permitidos desde metadata

```python
from app.domain.access import normalize_allowed_roles

metadata = {"allowed_roles": ["EMPLOYEE", "employee", None, " "]}
allowed_roles = normalize_allowed_roles(metadata)
print(allowed_roles)  # lista limpia y consistente
```

### 4) Puertos: type-check de contratos (Protocols)

```python
from typing import Protocol
from uuid import UUID

from app.domain.entities import Workspace

class WorkspaceRepository(Protocol):
    def get(self, workspace_id: UUID) -> Workspace | None: ...

# Infrastructure implementa esta interfaz; Application depende del Protocol.
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nueva entidad:** agregarla en `entities.py` con invariantes mínimas (estado válido, transiciones consistentes).
2. **Nuevo objeto de valor:** ubicarlo en `value_objects.py` si es un tipo pequeño e inmutable.
3. **Nueva policy:** agregarla en `workspace_policy.py` (o archivo específico si crece), manteniéndola pura (sin IO).
4. **Nuevo normalizador:** agregarlo en `tags.py`/`access.py` (o archivo nuevo) con reglas explícitas y límites.
5. **Nuevo puerto:**
   - persistencia → `repositories.py`
   - servicios externos → `services.py`
   - cache transversal de embeddings → `cache.py`

6. **API pública:** re-exportar en `__init__.py` solo lo estable (lo que otros módulos deberían importar).
7. **Tests:** unit tests puros para policies/normalizadores/entidades (sin fixtures de DB ni HTTP).

## 🆘 Troubleshooting

- **Imports profundos por todo el proyecto** → falta re-export del dominio → revisar `domain/__init__.py` y exponer los símbolos estables.
- **Policy devuelve `False` inesperado** → actor incompleto o visibilidad no contemplada → revisar `workspace_policy.py` y el armado de `WorkspaceActor`.
- **`allowed_roles` termina vacío** → metadata mal formada o normalizador filtra todo → revisar `access.py` y la estructura real de `metadata`.
- **Tags “raros” o duplicados en UI/búsqueda** → normalización insuficiente → revisar `tags.py` (trim/dedup/límites).
- **Application depende de infraestructura por accidente** → imports cruzados (`infrastructure` dentro de `domain`) → buscar imports y cortar la dependencia moviendo el contrato a `services.py`/`repositories.py`.
- **Contratos de repositorio crecen sin cohesión** → métodos de varios agregados mezclados → separar por agregado en `repositories.py` (múltiples Protocols) para mantener ISP.

## 🔎 Ver también

- `../application/README.md` (orquestación de casos de uso)
- `../identity/README.md` (usuarios, roles y actor)
- `../interfaces/README.md` (adaptación a HTTP)
- `../infrastructure/README.md` (implementaciones concretas de los puertos)
- `../container.py` (composición e inyección de dependencias)
