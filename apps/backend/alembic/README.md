# Alembic (migraciones)

## 🎯 Misión
Configurar y ejecutar migraciones de esquema de base de datos usando Alembic, con conexión a Postgres y ejecución de scripts versionados.

**Qué SÍ hace**
- Define el entorno de migración (online/offline).
- Aplica scripts en `versions/` en orden.
- Lee `DATABASE_URL` y adapta el driver a psycopg.

**Qué NO hace**
- No define modelos ORM del dominio.
- No autogenera migraciones (no hay metadata de ORM).

**Analogía (opcional)**
- Es el historial de reformas del edificio: cada cambio queda registrado y ejecutable.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `env.py` | Archivo Python | Configura Alembic y la conexión a la DB. |
| 📄 `README.md` | Documento | Esta documentación. |
| 📄 `script.py.mako` | Documento | Template para nuevos scripts de migración. |
| 📁 `versions/` | Carpeta | Scripts versionados de migración. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: comando `alembic` + `DATABASE_URL`.
- **Proceso**: `env.py` configura el contexto y ejecuta `run_migrations_*`.
- **Output**: DDL aplicado en la base y versión registrada en `alembic_version`.

Tecnologías/librerías usadas aquí:
- Alembic, SQLAlchemy (solo para engine), psycopg.

Flujo típico:
- `env.py` transforma `postgres://` a `postgresql+psycopg://`.
- `get_target_metadata()` retorna `None` (migraciones manuales).
- Alembic aplica cada script en `versions/` hasta `head`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure (DB migrations).
- Recibe órdenes de: CLI de Alembic.
- Llama a: Postgres vía SQLAlchemy engine.
- Contratos y límites: no depende de modelos ORM del dominio.

## 👩‍💻 Guía de uso (Snippets)
Comandos típicos:
- `alembic upgrade head`
- `alembic revision -m "create_users_table"`

```python
from alembic import command
from alembic.config import Config

cfg = Config("alembic.ini")
command.current(cfg)
```

## 🧩 Cómo extender sin romper nada
- Crea una nueva revisión en `versions/` para cada cambio de esquema.
- No edites migraciones ya aplicadas en entornos compartidos.
- Escribe DDL manual (no hay autogenerate).
- Mantén coherente el orden de dependencias entre tablas.

## 🆘 Troubleshooting
- Síntoma: `Target database is not up to date` → Causa probable: migraciones pendientes → Mirar `alembic upgrade head`.
- Síntoma: `No module named psycopg` → Causa probable: deps no instaladas → Mirar `requirements.txt`.
- Síntoma: `DATABASE_URL` inválida → Causa probable: env mal seteada → Mirar `.env` y `env.py`.

## 🔎 Ver también
- [Migrations folder](../migrations/README.md)
- [Backend root](../README.md)
