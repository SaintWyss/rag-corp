# HTTP Routers (Controllers)

## 🎯 Misión

Contiene los "Controladores" de la API.
Cada archivo agrupa endpoints relacionados con un recurso o feature (`/chat`, `/workspaces`).

**Qué SÍ hace:**

- Define `@router.get/post/put`.
- Extrae datos del Request.
- Llama al Use Case.
- Maneja excepciones específicas de HTTP.

**Qué NO hace:**

- No contiene lógica de negocio.
- No accede a DB.

## 🗺️ Mapa del territorio

| Recurso         | Tipo       | Responsabilidad (en humano)                  |
| :-------------- | :--------- | :------------------------------------------- |
| `admin.py`      | 🐍 Archivo | Endpoints de administración (Users, System). |
| `documents.py`  | 🐍 Archivo | Endpoints para `/documents` (CRUD, Upload).  |
| `query.py`      | 🐍 Archivo | Endpoints para `/chat` y `/query` (RAG).     |
| `workspaces.py` | 🐍 Archivo | Endpoints para `/workspaces` (Management).   |

## ⚙️ ¿Cómo funciona por dentro?

Cada módulo define una variable `router = APIRouter()`.
Estos routers se agregan al router principal en `../routes.py`.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Controller.
- **Llama a:** Use Cases.

## 👩‍💻 Guía de uso (Snippets)

### Definir un router

```python
from fastapi import APIRouter
router = APIRouter(tags=["items"])

@router.get("/")
def list_items(): ...
```

## 🔎 Ver también

- [Schemas (DTOs)](../schemas/README.md)
