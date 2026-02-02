# Layer: Domain (Core Business Logic)

## 🎯 Misión

Esta carpeta es el **Núcleo Sagrado** de la aplicación.
Contiene las definiciones fundamentales del negocio, las reglas que deben cumplirse siempre y los contratos (Interfaces) que la infraestructura debe implementar.

**Qué SÍ hace:**

- Define Entidades (`Document`, `Chunk`, `Workspace`).
- Define Objetos de Valor (`ConfidenceScore`, `SourceReference`).
- Define Interfaces de Repositorios (Puertos).
- Implementa lógica pura de dominio (validaciones invariantes).

**Qué NO hace:**

- **NUNCA** importa de `infrastructure`, `api` o `application`.
- No sabe qué base de datos se usa.
- No sabe si la API es REST o GraphQL.

**Analogía:**
Son las Leyes de la Física de este universo. No importa si usas un coche de gasolina o eléctrico (Infra), la gravedad (Dominio) funciona igual.

## 🗺️ Mapa del territorio

| Recurso               | Tipo       | Responsabilidad (en humano)                                            |
| :-------------------- | :--------- | :--------------------------------------------------------------------- |
| `access.py`           | 🐍 Archivo | Reglas de acceso y permisos básicos.                                   |
| `audit.py`            | 🐍 Archivo | Definición de eventos de auditoría (qué se tracea).                    |
| `cache.py`            | 🐍 Archivo | Interfaces para servicios de caché.                                    |
| `entities.py`         | 🐍 Archivo | **Entidades Principales**. Clases ricas con datos y comportamiento.    |
| `repositories.py`     | 🐍 Archivo | **Puertos**. Clases abstractas (`Protocol` o `ABC`) para persistencia. |
| `services.py`         | 🐍 Archivo | Servicios de dominio (lógica que involucra múltiples entidades).       |
| `tags.py`             | 🐍 Archivo | Gestión de etiquetas/tags para documentos.                             |
| `value_objects.py`    | 🐍 Archivo | Objetos inmutables (ej. un Score, coordenadas de un Chunk).            |
| `workspace_policy.py` | 🐍 Archivo | Políticas complejas de aislamiento entre workspaces.                   |

## ⚙️ ¿Cómo funciona por dentro?

Es código Python puro (`dataclasses`, `Pydantic models` o clases estándar).
No tiene dependencias externas pesadas.

### Entidades (`entities.py`)

Modelan el estado. Ejemplo: Un `Document` tiene una lista de `Chunk`s y un estado (`PENDING`, `READY`).

### Puertos (`repositories.py`)

Definen _qué_ necesitamos guardar, pero no _cómo_.

```python
class DocumentRepository(Protocol):
    def save(self, doc: Document) -> None: ...
```

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Core Domain (Hexagon Core).
- **Recibe órdenes de:** `application` (Use Cases).
- **Es implementado por:** `infrastructure` (Adapters).

## 👩‍💻 Guía de uso (Snippets)

### Usar una Entidad

```python
from app.domain.entities import Document, DocumentStatus

doc = Document(
    title="Report.pdf",
    status=DocumentStatus.PENDING,
    workspace_id=some_uuid
)
# doc.calculate_something() # Comportamiento rico
```

### Definir un Puerto (Repository)

```python
from typing import Protocol
from app.domain.entities import Document

class DocumentRepository(Protocol):
    def get_by_id(self, doc_id: str) -> Document | None:
        ...
```

## 🧩 Cómo extender sin romper nada

1.  **Entidades:** Agrégalas en `entities.py`. Usa `dataclasses` si necesitas mutabilidad controlada o `Pydantic` si es puramente datos.
2.  **Reglas:** Si una regla aplica a una sola entidad, ponla en su clase. Si aplica a varias, usa `services.py`.

## 🆘 Troubleshooting

- **Síntoma:** `ImportError` circular.
  - **Causa:** Probablemente importaste algo de `application` dentro de `domain`. El dominio **no** debe tener imports externos.

## 🔎 Ver también

- [Capa de Aplicación (Quien usa el dominio)](../application/README.md)
- [Capa de Infraestructura (Quien implementa el dominio)](../infrastructure/README.md)
