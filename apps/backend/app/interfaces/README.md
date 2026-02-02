# Interfaces (adaptadores entrantes)

## 🎯 Misión
Concentrar las interfaces de entrada al backend (HTTP), convirtiendo requests en DTOs de aplicación y respuestas RFC7807.

**Qué SÍ hace**
- Define el borde HTTP del sistema.
- Mapea requests a use cases y resultados a responses.
- Centraliza schemas y routers.

**Qué NO hace**
- No contiene reglas de negocio (eso está en Application).
- No accede directamente a DB.

**Analogía (opcional)**
- Es la recepción del backend: recibe pedidos y los encamina.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📁 `api/` | Carpeta | Adaptador HTTP (FastAPI). |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: requests HTTP.
- **Proceso**: routers → schemas → use cases → error mapping.
- **Output**: respuestas JSON o streaming SSE.

Tecnologías/librerías usadas aquí:
- FastAPI, Pydantic.

Flujo típico:
- Router toma request y construye DTO.
- Llama al caso de uso en `app/application/usecases/`.
- Mapea errores a RFC7807.

## 🔗 Conexiones y roles
- Rol arquitectónico: Interface.
- Recibe órdenes de: clientes HTTP.
- Llama a: Application (use cases), Crosscutting (errores, config).
- Contratos y límites: interfaces solo adaptan; no contienen negocio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.interfaces.api.http.router import router

# router se incluye desde app/api/main.py
```

## 🧩 Cómo extender sin romper nada
- Crea un router nuevo en `api/http/routers/`.
- Define schemas en `api/http/schemas/`.
- Incluye el router en `api/http/router.py`.
- Mantén el mapeo de errores en `api/http/error_mapping.py`.

## 🆘 Troubleshooting
- Síntoma: `422` inesperado → Causa probable: schema inválido → Revisar `schemas/`.
- Síntoma: `500` sin detalle → Causa probable: error sin mapping → Revisar `error_mapping.py`.

## 🔎 Ver también
- [API HTTP](./api/http/README.md)
- [Use cases](../application/usecases/README.md)
