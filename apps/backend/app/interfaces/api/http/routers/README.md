# Routers HTTP

## 🎯 Misión
Definir los endpoints HTTP por feature y conectar cada request con su caso de uso correspondiente.

**Qué SÍ hace**
- Implementa endpoints de workspaces, documentos, query y admin.
- Aplica dependencias de auth/permisos.
- Mapea errores de use cases a RFC7807.

**Qué NO hace**
- No contiene lógica de negocio (delegada a Application).
- No define schemas (eso está en `../schemas/`).

**Analogía (opcional)**
- Son las “ventanillas” específicas del mostrador.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de routers segmentados. |
| 🐍 `admin.py` | Archivo Python | Endpoints administrativos. |
| 🐍 `documents.py` | Archivo Python | Endpoints de documentos. |
| 🐍 `query.py` | Archivo Python | Endpoints de búsqueda/ask/stream. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `workspaces.py` | Archivo Python | Endpoints de workspaces. |

## ⚙️ ¿Cómo funciona por dentro?
Request → Router → Schema/DTO → Application → Response:
- **Request**: FastAPI recibe el request.
- **Router**: el módulo correspondiente define el endpoint.
- **Schema**: Pydantic valida input/output.
- **Application**: se invoca el caso de uso.
- **Response**: JSON o streaming SSE.

Tecnologías/librerías usadas aquí:
- FastAPI, Pydantic.

## 🔗 Conexiones y roles
- Rol arquitectónico: Interface (HTTP adapter).
- Recibe órdenes de: clientes HTTP.
- Llama a: use cases de Application y helpers de `dependencies.py`.
- Contratos y límites: endpoints deben ser thin controllers.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.interfaces.api.http.routers import query_router

# router principal incluye query_router
```

## 🧩 Cómo extender sin romper nada
- Agrega un archivo nuevo en este directorio para un feature.
- Define schemas en `../schemas/`.
- Incluye el router en `../router.py`.
- Usa `error_mapping.py` para errores tipados.

## 🆘 Troubleshooting
- Síntoma: endpoint no visible → Causa probable: router no incluido → Revisar `../router.py`.
- Síntoma: 403 inesperado → Causa probable: permisos → Revisar `identity/*`.
- Síntoma: SSE no funciona → Causa probable: streaming handler → Revisar `query.py`.

## 🔎 Ver también
- [HTTP](../README.md)
- [Schemas](../schemas/README.md)
- [Use cases](../../../application/usecases/README.md)
