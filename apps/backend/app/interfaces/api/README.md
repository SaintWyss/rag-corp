# Interfaces API

## 🎯 Misión
Agrupar las interfaces de API del backend (actualmente HTTP) y sus adaptadores.

**Qué SÍ hace**
- Organiza el adaptador HTTP en un solo lugar.
- Expone routers, schemas y dependencias de la API.

**Qué NO hace**
- No define lógica de negocio.
- No implementa infraestructura.

**Analogía (opcional)**
- Es el “acceso principal” al backend vía API.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📁 `http/` | Carpeta | Adaptador HTTP (routers, schemas, helpers). |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: requests HTTP.
- **Proceso**: routers → DTOs → use cases → error mapping.
- **Output**: responses JSON o streaming.

Tecnologías/librerías usadas aquí:
- FastAPI, Pydantic.

## 🔗 Conexiones y roles
- Rol arquitectónico: Interface.
- Recibe órdenes de: clientes HTTP.
- Llama a: Application (use cases) y Crosscutting (errores/config).
- Contratos y límites: mantener adaptación HTTP sin lógica de negocio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.interfaces.api.http.routes import router

# router se monta en app/api/main.py
```

## 🧩 Cómo extender sin romper nada
- Crea routers nuevos en `http/routers/`.
- Agrega schemas en `http/schemas/`.
- Incluye el router en `http/router.py`.

## 🆘 Troubleshooting
- Síntoma: endpoint no aparece → Causa probable: router no incluido → Revisar `http/router.py`.
- Síntoma: errores sin RFC7807 → Causa probable: mapeo faltante → Revisar `http/error_mapping.py`.

## 🔎 Ver también
- [HTTP](./http/README.md)
- [API composition](../../api/README.md)
