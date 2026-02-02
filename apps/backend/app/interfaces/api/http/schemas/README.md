# Schemas HTTP

## 🎯 Misión
Definir los DTOs HTTP (request/response) para los endpoints de la API, con validación Pydantic y límites configurables.

**Qué SÍ hace**
- Modela payloads de entrada/salida para workspaces, documentos, query y admin.
- Aplica validaciones y constraints de tamaño.
- Mantiene contratos estables para los routers.

**Qué NO hace**
- No contiene lógica de negocio.
- No ejecuta queries ni servicios.

**Analogía (opcional)**
- Es el “formulario oficial” que todos los pedidos deben completar.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de schemas. |
| 🐍 `admin.py` | Archivo Python | DTOs de endpoints admin. |
| 🐍 `documents.py` | Archivo Python | DTOs de documentos (upload/list/get). |
| 🐍 `query.py` | Archivo Python | DTOs de búsqueda/ask/stream. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `workspaces.py` | Archivo Python | DTOs de workspaces. |

## ⚙️ ¿Cómo funciona por dentro?
Request → Schema → Application → Response:
- **Request**: FastAPI recibe JSON/form-data.
- **Schema**: Pydantic valida campos y límites.
- **Application**: el router crea DTOs de use case.
- **Response**: se serializa con schemas de salida.

Tecnologías/librerías usadas aquí:
- Pydantic.

## 🔗 Conexiones y roles
- Rol arquitectónico: Interface (DTOs HTTP).
- Recibe órdenes de: routers HTTP.
- Llama a: settings para límites (max_query_chars, max_top_k).
- Contratos y límites: schemas no deben depender de infraestructura.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.interfaces.api.http.schemas.query import AskReq

req = AskReq(query="¿Qué dice el contrato?")
```

## 🧩 Cómo extender sin romper nada
- Agrega un schema nuevo por endpoint y documenta campos.
- Usa límites de `crosscutting.config` para consistencia.
- Mantén nombres y tipos estables para clientes.

## 🆘 Troubleshooting
- Síntoma: `422` en requests válidos → Causa probable: límites muy bajos → Revisar `config.py`.
- Síntoma: campos faltantes → Causa probable: schema incorrecto → Revisar DTO correspondiente.

## 🔎 Ver también
- [Routers](../routers/README.md)
- [Crosscutting config](../../../../crosscutting/README.md)
