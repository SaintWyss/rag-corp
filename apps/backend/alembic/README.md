# alembic
Como un **historial ejecutable**: registra y aplica cambios de esquema en Postgres de forma reproducible.

## 🎯 Misión
Este directorio contiene el runtime de **Alembic** para versionar el esquema de base de datos. Se encarga de resolver la URL de conexión, ejecutar revisiones en orden y mantener el estado en `alembic_version`.

### Qué SÍ hace
- Define el entorno de migraciones (online/offline) en `env.py`.
- Normaliza `DATABASE_URL` a un driver compatible (`postgresql+psycopg://`).
- Ejecuta revisiones en `versions/` según `revision`/`down_revision`.
- Mantiene el estado de migración en la tabla `alembic_version`.

### Qué NO hace (y por qué)
- No genera migraciones automáticamente.
  - Razón: `target_metadata` es `None` (la app usa SQL directo).
  - Consecuencia: las migraciones se escriben a mano y se revisan como código.
- No define reglas de negocio.
  - Razón: solo contiene DDL y decisiones de esquema.
  - Consecuencia: la lógica vive en `app/` y en los repositorios.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía operativa de migraciones. |
| `env.py` | Archivo Python | Runtime de Alembic (URL, online/offline, configuración). |
| `script.py.mako` | Documento | Template de nuevas revisiones. |
| `versions/` | Carpeta | Revisiones versionadas del esquema. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** comando `alembic ...` + `DATABASE_URL`.
- **Proceso:**
  - `env.py` resuelve URL y configura el contexto.
  - Offline: genera SQL sin conectar.
  - Online: crea engine con `NullPool` y aplica migraciones en transacción.
  - `target_metadata` es `None`, por eso no se usa autogenerate.
- **Output:** esquema actualizado y `alembic_version` sincronizada.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** tooling de infraestructura (migraciones DB).
- **Recibe órdenes de:** CLI de Alembic.
- **Llama a:** PostgreSQL vía SQLAlchemy engine + driver `psycopg`.
- **Reglas de límites:** no depende de Domain/Application; solo DDL.

## 👩‍💻 Guía de uso (Snippets)
```bash
# Estado actual y heads
alembic current
alembic heads
```

```bash
# Migrar al último estado
alembic upgrade head
```

```bash
# Crear una nueva revisión (manual)
alembic revision -m "add_index_to_chunks"
```

```python
# Ejecución programática (tooling)
from alembic import command
from alembic.config import Config

cfg = Config("alembic.ini")
command.current(cfg)
```

## 🧩 Cómo extender sin romper nada
- Cada cambio de esquema = una nueva revisión en `versions/`.
- No edites revisiones ya aplicadas en entornos compartidos; crea una correctiva.
- Preferí DDL explícito (`op.create_table`, `op.add_column`, `op.create_index`).
- Si necesitás operaciones especiales, usá `op.execute(...)` y documentalo.
- Validación mínima antes de merge: `alembic upgrade head` en DB limpia.
- Tests: si el cambio impacta repos, agregá pruebas en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `Target database is not up to date`.
  - **Causa probable:** DB atrasada respecto del repo.
  - **Dónde mirar:** `alembic heads`.
  - **Solución:** `alembic upgrade head`.
- **Síntoma:** no conecta o conecta a una DB “equivocada”.
  - **Causa probable:** `DATABASE_URL` ausente/incorrecta.
  - **Dónde mirar:** `.env` y `env.py` (`get_url`).
  - **Solución:** setear `DATABASE_URL` correcto.
- **Síntoma:** `No module named psycopg`.
  - **Causa probable:** dependencias no instaladas.
  - **Dónde mirar:** `requirements.txt`.
  - **Solución:** instalar deps del backend.
- **Síntoma:** `permission denied to create extension "vector"`.
  - **Causa probable:** usuario sin permisos o pgvector no instalado.
  - **Dónde mirar:** logs de Postgres.
  - **Solución:** habilitar extensión o usar DB con pgvector.
- **Síntoma:** downgrade no funciona.
  - **Causa probable:** baseline no soporta `downgrade()`.
  - **Dónde mirar:** `versions/001_foundation.py`.
  - **Solución:** recrear DB de entorno (por ejemplo con reset local).

## 🔎 Ver también
- `../README.md`
- `../app/infrastructure/db/README.md`
- `../app/infrastructure/repositories/README.md`
