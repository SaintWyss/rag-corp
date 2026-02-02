# Layer: Alembic (Database Migrations Config)

## 🎯 Misión

Esta carpeta contiene la configuración necesaria para que **Alembic** gestione los cambios en el esquema de la base de datos PostgreSQL.
Define cómo conectarse a la base de datos para ejecutar migraciones y cómo generar nuevos scripts de revisión.

**Qué SÍ hace:**

- Configura el entorno de ejecución de migraciones (`env.py`).
- Define la plantilla para nuevas migraciones (`script.py.mako`).
- Almacena el historial de versiones en `versions/`.

**Qué NO hace:**

- No define tablas (eso está en `infrastructure/db`).
- No ejecuta consultas de negocio.

**Analogía:**
Es el libro de bitácora de la construcción. Registra cada pared que se levantó y cada tubería que se movió, para que cualquiera pueda reconstruir el edificio desde cero.

## 🗺️ Mapa del territorio

| Recurso          | Tipo        | Responsabilidad (en humano)                                                   |
| :--------------- | :---------- | :---------------------------------------------------------------------------- |
| `env.py`         | 🐍 Archivo  | **Script Crítico**. Configura la conexión SQLAlchemy para correr migraciones. |
| `versions/`      | 📁 Carpeta  | Contiene los scripts individuales de migración (`.py`).                       |
| `script.py.mako` | 📄 Template | Plantilla Mako para generar nuevos archivos de migración.                     |

## ⚙️ ¿Cómo funciona por dentro?

**Nota Importante de Diseño:**
Esta aplicación utiliza **Raw SQL (psycopg)** en sus repositorios y no define modelos ORM de SQLAlchemy completos.
Por lo tanto, **NO hay autogeneración automática** de migraciones (`--autogenerate` no detectará cambios).

**Flujo:**

1.  `env.py` lee `DATABASE_URL` del entorno.
2.  Si es modo `online`, crea un Engine y conecta.
3.  Si es modo `offline`, genera solo el SQL.
4.  Alembic busca la tabla `alembic_version` en la DB para saber en qué revisión está.
5.  Aplica los scripts de `versions/` secuencialmente hasta llegar a `head`.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Database Schema Management.
- **Recibe órdenes de:** CLI de Alembic (`alembic upgrade head`).
- **Llama a:** PostgreSQL (ddl).

## 👩‍💻 Guía de uso (Snippets)

### Crear una nueva migración (Manual)

Dado que no usamos ORM metadata, debemos escribir el SQL/DDL a mano (o usando helpers de alembic).

```bash
alembic revision -m "create_users_table"
```

Luego editar el archivo generado en `versions/`:

```python
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        # ...
    )
```

### Aplicar cambios

```bash
alembic upgrade head
```

## 🧩 Cómo extender sin romper nada

1.  **Nunca** modifiques una migración que ya ha sido mergeada a `main`. Crea una nueva revisión para corregir.
2.  **Naming:** Usa nombres descriptivos para las revisiones.

## 🆘 Troubleshooting

- **Síntoma:** "Target database is not up to date".
  - **Causa:** Tu código espera tablas que aún no existen en tu DB local.
  - **Solución:** `alembic upgrade head`.
- **Síntoma:** `alembic` command not found.
  - **Solución:** `pip install -r requirements.txt`.
