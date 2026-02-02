# Scripts de mantenimiento

## 🎯 Misión
Este directorio contiene herramientas de línea de comandos para tareas administrativas y de documentación del backend.

**Qué SÍ hace**
- Crea usuarios admin directamente en Postgres.
- Exporta el esquema OpenAPI desde la app FastAPI.
- Permite tareas operativas sin levantar toda la API.

**Qué NO hace**
- No reemplaza flujos de negocio ni endpoints HTTP.
- No contiene migraciones de DB (eso está en `alembic/`).

**Analogía (opcional)**
- Son “llaves de servicio” para tareas específicas del backend.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🧰 `create_admin.py` | Script | Crea un usuario admin en la tabla `users` (idempotente). |
| 🧰 `export_openapi.py` | Script | Exporta el esquema OpenAPI a un archivo JSON. |
| 📄 `README.md` | Documento | Esta documentación. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: argumentos CLI (email, password, output path).
- **Proceso**: conexión directa a Postgres o generación de OpenAPI desde `app.api.main`.
- **Output**: usuario creado en DB o archivo JSON con el schema.

Tecnologías/librerías usadas aquí:
- argparse, psycopg, FastAPI (solo para exportar OpenAPI).

Flujo típico:
- `create_admin.py` valida env y escribe en `users`.
- `export_openapi.py` carga la app y serializa el schema.

## 🔗 Conexiones y roles
- Rol arquitectónico: Tooling.
- Recibe órdenes de: operadores/desarrolladores por CLI.
- Llama a: Postgres (psycopg) y `app.api.main`.
- Contratos y límites: scripts no deben importar infraestructura compleja ni casos de uso.

## 👩‍💻 Guía de uso (Snippets)
```python
from scripts.export_openapi import _resolve_app
from app.api.main import app

schema = _resolve_app(app).openapi()
```

## 🧩 Cómo extender sin romper nada
- Crea un script nuevo con `argparse` y una función `main()`.
- Usa imports explícitos y evita side‑effects al importar.
- Documenta variables de entorno requeridas en este README.
- Mantén los scripts idempotentes cuando escriban en DB.

## 🆘 Troubleshooting
- Síntoma: `DATABASE_URL is required` → Causa probable: env faltante → Mirar `.env` y `create_admin.py`.
- Síntoma: export OpenAPI falla → Causa probable: import error en la app → Mirar `app/api/main.py`.
- Síntoma: permisos insuficientes en DB → Causa probable: credenciales → Mirar `.env`.

## 🔎 Ver también
- [API composition](../app/api/README.md)
- [Alembic](../alembic/README.md)
