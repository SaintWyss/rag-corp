# HTTP Schemas (Data Contracts)

## 🎯 Misión

Define los contratos de datos (Data Transfer Objects - DTOs) para la API.
Utiliza **Pydantic** para validar que los JSONs de entrada y salida cumplan con el formato esperado.

**Qué SÍ hace:**

- Valida tipos (int, str, email).
- Documenta ejemplos para OpenAPI/Swagger.
- Sanitiza inputs.

**Qué NO hace:**

- No son Entidades de Dominio (aunque se parezcan).

## 🗺️ Mapa del territorio

| Recurso        | Tipo       | Responsabilidad (en humano)                   |
| :------------- | :--------- | :-------------------------------------------- |
| `admin.py`     | 🐍 Archivo | Schemas para administración.                  |
| `model.py`     | 🐍 Archivo | Schemas base genéricos (ej. `ErrorResponse`). |
| `chat.py`      | 🐍 Archivo | Requests/Responses para Chat.                 |
| `document.py`  | 🐍 Archivo | Requests/Responses para Documentos.           |
| `workspace.py` | 🐍 Archivo | Requests/Responses para Workspaces.           |

## ⚙️ ¿Cómo funciona por dentro?

Heredan de `pydantic.BaseModel`.
Usa `ConfigDict(from_attributes=True)` para mapear fácilmente desde objetos de Dominio/ORM.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Data Contracts.
- **Usado por:** Routers.

## 👩‍💻 Guía de uso (Snippets)

### Definir un Schema

```python
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    email: str = Field(..., description="Email corporativo")
    age: int | None = None
```

## 🧩 Cómo extender sin romper nada

1.  **Breaking Changes:** Evita renombrar campos en Schemas de respuesta. Si lo haces, rompes el Frontend.

## 🔎 Ver también

- [Routers](../routers/README.md)
