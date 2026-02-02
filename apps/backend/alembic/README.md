# Alembic (migraciones de esquema)

## 🎯 Misión

Esta carpeta define el **runtime de Alembic** para versionar y aplicar cambios de esquema en PostgreSQL de forma **reproducible**.

Acá se resuelven tres problemas operativos, sin mezclarlos con el código de negocio:

1. **Cómo conectarse** a la DB para migrar (a partir de `DATABASE_URL`).
2. **Cómo ejecutar** revisiones (`versions/`) en orden y registrar el estado (`alembic_version`).
3. **Cómo mantener disciplina de evolución** del esquema (migraciones manuales, sin “magia” de autogeneración).

Analogía breve: esto es el **historial ejecutable** del edificio. No describe el negocio (eso está en `app/`), pero sí cada reforma estructural (tablas, índices, constraints).

**Qué SÍ hace**

* Configura el entorno de migración (online/offline) en `env.py`.
* Resuelve `DATABASE_URL` y normaliza el driver a `postgresql+psycopg://...`.
* Ejecuta scripts en `versions/` respetando el grafo `revision` / `down_revision`.
* Registra el estado en la tabla `alembic_version` (la DB “recuerda” hasta dónde migró).

**Qué NO hace (y por qué)**

* No define modelos ORM del dominio: este proyecto opera principalmente con **Raw SQL**.

  * **Consecuencia:** no existe una `MetaData` del ORM que represente el esquema “real” de negocio.
* No usa autogenerate (ni promete drift checks automáticos).

  * **Consecuencia:** cada migración se escribe **a mano** y se revisa como código de infraestructura.

---

## 🗺️ Mapa del territorio

| Recurso             | Tipo           | Responsabilidad (en humano)                                                          |
| :------------------ | :------------- | :----------------------------------------------------------------------------------- |
| 🐍 `env.py`         | Archivo Python | Runtime de Alembic: URL/driver, configuración de contexto, ejecución online/offline. |
| 📄 `script.py.mako` | Documento      | Template de nuevas revisiones (cómo luce un archivo en `versions/`).                 |
| 📁 `versions/`      | Carpeta        | Historial de revisiones (una por archivo).                                           |
| 📄 `README.md`      | Documento      | Guía operativa + convenciones de migraciones para el equipo.                         |

> Nota: dentro de `versions/` existe un `.gitkeep` para asegurar la carpeta en git. No forma parte del runtime.

---

## ⚙️ ¿Cómo funciona por dentro?

### 1) Identificadores de Alembic (cómo entiende el “orden”)

Cada archivo en `versions/` define:

* `revision`: ID único de la revisión (en este repo se usa formato humano, ej. `001_foundation`).
* `down_revision`: la revisión inmediatamente anterior (o `None` para la baseline).
* `upgrade()`: aplica cambios.
* `downgrade()`: revierte cambios (en este repo, la baseline declara explícitamente “NO soportado”).

Alembic construye un DAG con esos IDs y aplica todo lo que falte desde `current` hasta `head`.

### 2) Resolución de conexión (DATABASE_URL → SQLAlchemy URL)

En este repo, `env.py` implementa una normalización explícita:

* Lee `DATABASE_URL` y, si no existe, usa default local:

  * `postgresql://postgres:postgres@localhost:5432/rag`
* Si la URL viene como `postgresql://...` o `postgres://...`,
  la convierte a:

  * `postgresql+psycopg://...`

Esto es clave porque Alembic usa SQLAlchemy **solo como motor de conexión**, y necesita el “dialect+driver” correcto.

### 3) target_metadata y por qué no hay autogenerate

`get_target_metadata()` devuelve `None` con una nota explícita: la app usa Raw SQL, así que **no hay metadata ORM**.

Implicación técnica:

* `alembic revision --autogenerate` no es confiable (no tiene contra qué comparar).
* `context.configure(compare_type=True, compare_server_default=True)` se habilita **solo** si existiera metadata (no es el caso).

### 4) Offline vs Online (qué cambia de verdad)

**Offline mode**

* No abre conexión real.
* Alembic genera SQL usando:

  * `literal_binds=True` y `dialect_opts={"paramstyle": "named"}`
* Útil para inspección:

  * `alembic upgrade head --sql`

**Online mode**

* Crea un engine con `engine_from_config(...)` y `poolclass=NullPool`.

  * `NullPool` es intencional: migraciones son procesos “one-shot”, no conviene pool persistente.
* Abre una conexión y corre:

  * `with context.begin_transaction(): context.run_migrations()`

### 5) Migración fundacional `001_foundation.py` (baseline)

`versions/001_foundation.py` es la **migración baseline** (estado inicial del esquema). Sus decisiones forman parte del contrato del sistema:

**Extensiones**

* `CREATE EXTENSION IF NOT EXISTS vector` (pgvector).

**Tablas base**

* `workspaces`
* `users`
* `documents`
* `chunks`
* `audit_events`
* `workspace_acl`

**Decisiones técnicas relevantes**

* Columnas `JSONB` con `server_default` seguro (evitar `NULL` inesperado).
* Arrays con índices `GIN` para filtros eficientes.
* Soft delete con `deleted_at` + índice parcial en consultas principales.
* `chunks.embedding` como `vector(768) NOT NULL` (contrato de dimensión).
* Optimizaciones avanzadas (ej. HNSW/trigram) quedan comentadas como opción futura, para evitar complejidad prematura.

> Si necesitás entender el “contrato DB” real, `001_foundation.py` es la referencia primaria. La lógica de consultas vive en los repositorios.

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** Tooling de infraestructura (migraciones DB).
* **Recibe órdenes de:** CLI de Alembic.
* **Llama a:** PostgreSQL a través de SQLAlchemy engine usando driver `psycopg`.
* **Límites:**

  * No depende de Domain/Application.
  * No define reglas de negocio: solo DDL y decisiones de esquema.

---

## 👩‍💻 Guía de uso (operación diaria)

> Recomendación operativa: ejecutar comandos desde `apps/backend/` (donde vive `alembic.ini`).

### Inspección (estado de tu DB)

```bash
# Revisión aplicada en esta DB
alembic current

# Última revisión disponible en el repo
alembic heads

# Historial completo
alembic history
```

### Aplicar migraciones

```bash
# Migrar al estado más nuevo
alembic upgrade head

# Migrar paso a paso (útil para debugging)
alembic upgrade +1
```

### Generar SQL sin ejecutar (offline)

```bash
alembic upgrade head --sql
```

### Crear una nueva migración (manual)

```bash
alembic revision -m "add_index_to_chunks"
```

> Importante: **no uses `--autogenerate`** en este repo, porque `target_metadata=None`.

### Casos especiales

**Marcar una DB como “ya migrada” (sin ejecutar DDL)**

```bash
alembic stamp head
```

**Dos heads (branching de migraciones)**

```bash
alembic heads
alembic merge -m "merge heads" <head1> <head2>
```

### Ejecución programática (tooling)

```python
from alembic import command
from alembic.config import Config

cfg = Config("alembic.ini")

command.current(cfg)
# command.upgrade(cfg, "head")
```

---

## 🧩 Cómo extender sin romper nada (convenciones fuertes)

1. **Una revisión por cambio de esquema** (002+, 003+, …). No apiles cambios “en caliente”.
2. **Nunca edites migraciones ya aplicadas** en un entorno compartido (CI/prod).

   * Si hubo error: creá una nueva migración correctiva.
3. **DDL explícito**: preferí `op.create_table`, `op.add_column`, `op.create_index`.

   * Si algo es muy específico, `op.execute(...)` es válido (y a veces más claro).
4. **Convención de nombres (consistencia operativa)**:

   * `pk_<tabla>`
   * `uq_<tabla>_<col>`
   * `ix_<tabla>_<col>`
   * `fk_<tabla>_<col>__<ref_tabla>`
5. **Pensá en locks y tiempos**:

   * Evitá cambios destructivos grandes en una sola migración.
   * En tablas grandes, preferí cambios por etapas (columna nullable → backfill → constraint).
6. **Índices concurrentes (solo si hace falta)**

   * PostgreSQL no permite `CREATE INDEX CONCURRENTLY` dentro de una transacción.
   * Si lo necesitás, usá autocommit en la migración y documentalo en el header.
7. **Validación mínima antes de merge**:

   * DB limpia → `alembic upgrade head`
   * DB con estado previo → `alembic upgrade head`
   * (si aplica) test de integración que valide existencia de tabla/índice crítico

---

## 🆘 Troubleshooting

* **Síntoma:** `Target database is not up to date`

  * **Causa probable:** la DB está atrasada respecto del repo.
  * **Solución:** `alembic upgrade head`.

* **Síntoma:** no conecta o conecta a una DB “equivocada”

  * **Causa probable:** `DATABASE_URL` ausente/incorrecta; o viene como `postgres://`.
  * **Qué mirar:** `DATABASE_URL` del entorno y la función de normalización en `env.py`.

* **Síntoma:** `No module named psycopg`

  * **Causa probable:** deps no instaladas.
  * **Solución:** `pip install -r requirements.txt`.

* **Síntoma:** `permission denied to create extension "vector"`

  * **Causa probable:** usuario sin permisos o Postgres sin pgvector.
  * **Qué mirar:** logs del Postgres y el servicio DB del entorno.

* **Síntoma:** aparecen dos heads después de merges paralelos

  * **Causa probable:** migraciones creadas en ramas distintas apuntaron al mismo `down_revision`.
  * **Solución:** `alembic merge ...` para unificar el grafo.

---

## 🔎 Ver también

* [Backend root](../README.md)
* [DB adapter (pool/sesiones)](../app/infrastructure/db/README.md)
* [Repositorios](../app/infrastructure/repositories/README.md)
* [Migrations folder](../migrations/README.md)
