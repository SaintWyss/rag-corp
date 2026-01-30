"""
============================================================
TARJETA CRC (Class / Responsibilities / Collaborators)
============================================================
Class: alembic/env.py (Alembic Environment Configuration)

Responsibilities:
  - Definir el runtime de Alembic para migraciones (online/offline).
  - Proveer la URL de conexión a la DB a partir de DATABASE_URL.
  - Exponer target_metadata del ORM para autogenerate (si aplica).
  - Enforzar naming convention estable (si hay ORM metadata).
  - Configurar comparación (type/default) para evitar drift cuando autogenerate está activo.

Collaborators:
  - Alembic (context, config)
  - SQLAlchemy Engine (engine_from_config)
  - ORM metadata (Base.metadata)
  - PostgreSQL (driver psycopg)

Policy:
  - Si no hay ORM metadata disponible, migraciones manuales siguen funcionando.
  - Autogenerate requiere target_metadata != None.
============================================================
"""

import os
from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.schema import MetaData

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s__%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _sqlalchemy_url(raw_url: str) -> str:
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    return raw_url


def get_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/rag",
    )
    return _sqlalchemy_url(url)


def get_target_metadata() -> Optional[MetaData]:
    """
    Si hay ORM, devolvemos Base.metadata para autogenerate.
    Si no hay ORM o el import falla, devolvemos None:
    - migraciones manuales funcionan
    - autogenerate queda deshabilitado
    """
    try:
        # ⚠️ Ajustar a tu proyecto si cambia la ubicación de Base
        from app.db.base import Base  # type: ignore

        Base.metadata.naming_convention = NAMING_CONVENTION
        return Base.metadata

    except Exception as exc:
        # Log warning (print es seguro; Alembic context aún no existe aquí)
        print(
            f"[alembic] WARNING: target_metadata no disponible (autogenerate deshabilitado). Motivo: {exc}"
        )
        return None


target_metadata: Optional[MetaData] = get_target_metadata()


def _configure_context(connection: Connection | None = None) -> None:
    """
    Config centralizada para Alembic.
    Si no hay target_metadata, evitamos opciones de comparación para no “vender humo”.
    """
    common_kwargs = dict(
        target_metadata=target_metadata,
        include_schemas=False,
        version_table="alembic_version",
    )

    if target_metadata is not None:
        common_kwargs.update(
            compare_type=True,
            compare_server_default=True,
        )

    if connection is None:
        context.configure(
            url=get_url(),
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            **common_kwargs,
        )
    else:
        context.configure(connection=connection, **common_kwargs)


def run_migrations_offline() -> None:
    _configure_context(connection=None)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _configure_context(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
