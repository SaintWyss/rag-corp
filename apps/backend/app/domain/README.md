# Domain Layer

## 🎯 Propósito y Filosofía

Esta capa (`app/domain`) es el **núcleo** del sistema RAG. Contiene la lógica de negocio pura, las reglas empresariales y los contratos abstractos.

**Regla de Oro:**

> El Dominio NO depende de nadie. El resto depende del Dominio.

🚫 **Prohibido:**

- Importar FastAPI, Pydantic, SQLAlchemy, Boto3, Redis.
- Acceder a bases de datos o sistemas de archivos directamente.
- Depender de `config` o variables de entorno.

✅ **Permitido:**

- Definir `dataclasses` puros (Entidades, Value Objects).
- Definir `Protocols` (Interfaces) para repositorios y servicios.
- Lógica de negocio pura (validaciones de estado, cálculos).

---

## 🧩 Estructura

| Módulo                | Contenido                                                                                                      |
| :-------------------- | :------------------------------------------------------------------------------------------------------------- |
| `entities.py`         | **Entidades**: Objetos con identidad (ID). Ej: `Document`, `Workspace`, `User`.                                |
| `value_objects.py`    | **Value Objects**: Conceptos inmutables definidos por sus atributos. Ej: `ConfidenceScore`, `SourceReference`. |
| `repositories.py`     | **Puertos (Data)**: Contracts para persistencia. Ej: `DocumentRepository` (Protocol).                          |
| `cache.py`            | **Puertos (Cache)**: Contract para caché key-value (Embeddings). Ej: `EmbeddingCachePort` (Protocol).          |
| `services.py`         | **Puertos (Servicios)**: Contracts para sistemas externos. Ej: `LLMService`, `EmbeddingService`.               |
| `workspace_policy.py` | **Políticas**: Reglas complejas de decisión aisladas. Ej: ¿Quién puede ver este workspace?                     |
| `audit.py`            | **Auditoría**: Definición de eventos de compliance.                                                            |

---

## 💡 Conceptos Clave

### Entidades Ricas (pero no pesadas)

Las entidades no son solo datos ("anemia"). Tienen métodos que protegen sus invariantes de negocio básicas.

- _Ejemplo_: `workspace.archive()` gestiona la fecha de archivado y valida el estado.

### Inmutabilidad donde es posible

Usamos `frozen=True` y `slots=True` extensivamente para `value_objects` y dondesea posible en `entities` para garantizar seguridad y performance.

### Inversión de Dependencias (DIP)

El dominio define **qué** necesita (ej: `save_document`), pero no **cómo** se hace.
La capa de Infraestructura implementa estos Protocolos (ej: `PostgresDocumentRepository`).
La capa de Aplicación (Use Cases) inyecta la implementación concreta en tiempo de ejecución.

---

## 🔍 Ejemplos

### Value Object (Confidence Score)

```python
score = calculate_confidence(...)  # Retorna ConfidenceScore
if score.level == "low":
    # Lógica de negocio basada en el VO
    return "Consulte con un experto."
```

### Protocol (Repository)

```python
class DocumentRepository(Protocol):
    def get_document(self, id: UUID) -> Document | None: ...
```

_(No hay SQL aquí. Solo el contrato)._
